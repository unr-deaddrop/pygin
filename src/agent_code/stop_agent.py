"""
Stop the agent.

In general, this should be invoked as a subprocess call.
"""

import argparse
import logging
import os
import re
import shlex
import subprocess
import sys
import time

import psutil

logging.basicConfig(
    handlers=[logging.StreamHandler(sys.stdout)],
    level=logging.DEBUG,
    format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()

TARGET_CMDLINES = [
    "-m src.agent_code.main",
    "celery -A src.agent_code.tasks worker",
    "celery -A src.agent_code.tasks beat",
    "redis-server",
]


def read_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="stop_agent")

    parser.add_argument(
        "delay",
        type=int,
        default=60,
        nargs="?",
        help="The delay before killing all processes.",
        metavar="delay",
    )

    return parser.parse_args()


def kill_docker() -> None:
    # Maybe this works, don't know
    subprocess.run(shlex.split("docker compose stop"))


if __name__ == "__main__":
    args = read_args()

    # Wait for the specified delay time
    time.sleep(args.delay)

    # If this is a Docker container, invoke docker compose stop
    # from inside the container itself
    if os.getenv("IS_DOCKER") == "True":
        kill_docker()

    # Otherwise, levy psutil to just kill everything the hard way
    for proc in psutil.process_iter():
        try:
            # Check whether the process name matches
            for cmdline in TARGET_CMDLINES:
                cmdline_str = " ".join(proc.cmdline())
                if re.search(cmdline, cmdline_str):
                    logger.warning(f"Killing {cmdline_str} ({proc.cmdline()=})")
                    proc.kill()
                    break
        except psutil.AccessDenied:
            # Ignore permission errors
            logger.debug(f"Failed to access data for {proc.pid=}")
        except Exception as e:
            # Covers everything else, like TOCTOU
            logger.debug(f"Error trying to access {proc.pid=}: {e}")
