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

from src.agent_code import config
from src.agent_code import tasks
from src.agent_code import utility
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
    cfg_obj: config.PyginConfig, redis_con: redis.Redis, remove_msgs: bool = True
) -> list[PyginMessage]:
    """
    Get and reconstruct all messages remaining in the Redis database.

    Note that this does not actually invoke the message retreival system;
    it assumes that a scheduled Celery task is responsible for initating
    remote message retrieval over a particular protocol.


    """
    raise NotImplementedError


def get_stored_tasks(
    app: celery.Celery, prefix: str = "celery-task-meta-"
) -> list[AsyncResult]:
    """
    Get all task results currently stored in the Redis database.

    By default, this assumes that the default Celery prefix ("celery-task-meta-")
    is in use when storing task information in the Redis database.
    """
    raise NotImplementedError


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
    
    """
    TODO: There's a few paths forward that make sense.
    
    One is to do exactly the below. However, this implies that we're willing to
    basically call `time.sleep(...)` to keep us from just trying to get new messages
    all the time, which should really be delegated to celery beat.
    
    The other is to allow celery beat to actually execute the "get new messages"
    task periodically, and have both "get new messages" and "check for completed 
    commands" store something searchable in the database that can be performed
    anytime at will. Perhaps these new messages could be stored in a Redis key
    that the server simply looks at, such that you have:
    - Periodic task starts
    - Periodic task finishes
    - Periodic task stores result in some named Redis key based on config
    - Periodic task stores named Redis key in another Redis set based on config
    - Main process grabs the Redis set (from step 4) and finds all of the
      *actual* results by querying Redis keys stored in the set, deleting 
      elements in the set and the associated keys as it goes.
    
    This sidesteps the issue of the main process dying and not acting on incoming
    messages, since when the main process restarts, it'll see that the database
    still has all of those unread messages. On the other hand, there's still 
    a few risks, and it's still a little messier than I'd like. But hey, no more
    having to time.sleep()!
    
    
    Ultimately, the challenge is to just prevent the "get new messages" call from
    happening way too often. Yet another option is to use bound tasks, such that
    any results for "get new messages" is stored within a specified Redis key
    that can trivially be obtained with a helper function in main.py.
    (https://docs.celeryq.dev/en/latest/userguide/tasks.html#bound-tasks)
    ---
    
    We could also set some flag in tasks.py periodically that prevents "get
    new messages" from executing unless that flag is set. Then, invoking the
    the messaging system happens in real-time, but whether or not it actually
    completes depends on whether the periodic task has run recently. However,
    I don't think that actually works with Celery, especially because state
    isn't shared among worker processes (as far as I know). So this isn't robust.
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
