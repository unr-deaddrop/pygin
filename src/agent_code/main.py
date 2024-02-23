"""
The main process loop.
"""

from pathlib import Path
import argparse
import celery

# import redis

# from celery.result import AsyncResult

from src.agent_code import config
from src.agent_code import tasks

DEFAULT_CFG_PATH = Path("./agent.cfg")


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


def entrypoint(cfg_obj: config.Config, app: celery.Celery) -> None:
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

    cfg_obj = config.Config.from_cfg_file(args.cfg_path)
    # Create any required directory structure
    cfg_obj.create_dirs()

    # entrypoint(cfg_obj, tasks.app)
