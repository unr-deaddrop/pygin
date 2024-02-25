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
    redis_con: redis.Redis, 
    remove_msgs: bool = True
) -> list[PyginMessage]:
    """
    Get and reconstruct all messages remaining in the Redis database.
    
    Note that this does not actually invoke the message retreival system;
    it assumes that a scheduled Celery task is responsible for initating
    remote message retrieval over a particular protocol.
    
    
    """
    raise NotImplementedError

def get_stored_tasks(
    app: celery.Celery,
    prefix: str = "celery-task-meta-"
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
    pass


if __name__ == "__main__":
    args = get_args()

    # Load configuration from path specified on the command line. Note that 
    # this also implicitly creates the directories specified in the configuration
    # file, if they don't already exist.
    cfg_obj = config.PyginConfig.from_cfg_file(args.cfg_path)

    # Start the main agent loop with the new configuration information and the
    # global Celery tasking.
    # entrypoint(cfg_obj, tasks.app)
