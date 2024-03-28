"""
Modify the Docker Compose files so that they use `cache_from`, providing a set
of standard layers that can be reused. Then, invoke the build command 
(synchronously) for the "base" Docker Compose file to generate the layers.
"""

from pathlib import Path
from typing import Any
# import subprocess
# import shlex
import logging
import sys

import yaml

from src.meta.agent import PyginInfo

logging.basicConfig(
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
    level=logging.DEBUG,
    format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

# The name of the image to use.
IMAGE_NAME = PyginInfo.name + "-" + PyginInfo.version + ":latest"

# A list of services that will use the referenced image.
SERVICE_NAMES = [
    "pygin",
    "celery_beat",
    "celery_worker",
    "pygin_build",
    "pygin_message",
]

# The list of Compose files to edit.
COMPOSE_FILES = [
    "docker-compose.yml",
    "resources/install/docker-compose-payload.yml",
    "resources/install/docker-compose-messaging.yml",
]

if __name__ == "__main__":
    for filename in COMPOSE_FILES:
        compose_path = Path(filename).resolve()
        if not compose_path.exists():
            logger.warning(f"Missing {filename} at {compose_path}, skipping")
            continue

        logger.info(f"Overwriting {compose_path}")
        with open(compose_path.resolve()) as fp:
            data: dict[str, Any] = yaml.safe_load(fp)

        # Search for each specified service name. If present, tack on the image
        # name and use it as the cache_from.
        for service_name in SERVICE_NAMES:
            if service_name not in data["services"]:
                continue

            data["services"][service_name]["image"] = IMAGE_NAME
            data["services"][service_name]["build"]["cache_from"] = [IMAGE_NAME]

        # Rewrite the files
        with open(compose_path, "wt+") as fp:
            yaml.dump(data, fp)

    # The below is deprecated in favor of doing this inside the Makefile

    # Build the base image, which should be the most expansive image, to cache
    # the associated layers that can then be reused across the other Compose
    # stacks
    # logger.info("Building base image (this may take a while!)")
    # p = subprocess.run(shlex.split("docker compose build"), capture_output=True, check=True)
    # logger.info(f"{p.stdout=} {p.stderr=}")
