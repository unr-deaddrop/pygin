"""
The main process loop.
"""

from pathlib import Path
import argparse
import logging
import sys

from celery.result import AsyncResult
import celery
import redis

# from celery.result import AsyncResult

from src.agent_code import config, utility
from src.protocols._shared_lib import PyginMessage

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
    remove_msgs: bool = True
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
    :param remove_msgs: Whether to delete the task result entries in Redis 
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
        AsyncResult(task_id, app=app). # TODO LOOK AT ME
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
    """
    # Invoke the "get new messages task". Store the AsyncResult in a list.

    # Check if any of the "get new messages" tasks in previous runs have completed.
    # If so, retrieve their results and delete the associated task from the Redis
    # database.

    # For each message receieved (which should always be command_request), invoke
    # the command execution task. Store that AsyncResult in a list.

    # Check if any of the command executions have finished. If so, log it, and
    # then invoke the "send message" task.

    raise NotImplementedError


if __name__ == "__main__":
    args = get_args()

    # Load configuration from path specified on the command line. Note that
    # this also implicitly creates the directories specified in the configuration
    # file, if they don't already exist.
    cfg_obj = config.PyginConfig.from_cfg_file(args.cfg_path)

    # Start the main agent loop with the new configuration information and the
    # global Celery tasking.
    # entrypoint(cfg_obj, tasks.app)
