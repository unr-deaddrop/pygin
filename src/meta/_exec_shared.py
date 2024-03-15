"""
Performs a bunch of Docker Compose overhead stuff.
"""
from typing import Any
from pathlib import Path
import logging
import random
import shlex
import string
import sys
import subprocess
import yaml

logger = logging.getLogger(__name__)

RANDOM_CHARSET = string.ascii_lowercase + string.digits


def overwrite_compose_file(compose_path: Path, service_name: str, container_name: str):
    """
    Overwrite a particular service in a Compose file with a random name.
    """

    logger.info(f"Overwriting {compose_path.resolve()}")
    with open(compose_path.resolve()) as fp:
        data: dict[str, Any] = yaml.safe_load(fp)

    # Overwrite the service and container names accordingly
    data["services"][service_name]["container_name"] = container_name
    data["services"][container_name] = data["services"].pop(service_name)

    # Rewrite the file
    with open("docker-compose-payload.yml", "wt+") as fp:
        yaml.dump(data, fp)


def run_compose_file(
    compose_name: Path, service_name: str, stdout_file: Path, copy_out: list[str]
):
    """
    Run a compose file to completion using a randomized container name.

    :param compose_name: The path to the Docker Compose file to invoke.
    :param service_name: The name of the service to overwrite with a random name.
    :param stdout_file: The path to write the Docker Compose stdout to.
    :param copy_out: What files to copy out of the container. Note that a base
        of /app/ is assumed.
    """
    # Generate a random container name with reasonably low collision chance
    # https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits
    container_name = "".join([random.choice(RANDOM_CHARSET) for _ in range(16)])
    logger.info(f"Selected {container_name=}")

    # Overwrite the pygin_build service with a random name
    overwrite_compose_file(compose_name, service_name, container_name)

    # Run Docker Compose to completion, capturing its output (this avoids having
    # to manually hunt down the logs or redirecting the output in other ways)
    logger.info("Starting Docker Compose")
    command = shlex.split(f"docker compose -f {compose_name} up")
    p = subprocess.run(command, capture_output=True)
    logger.info("Docker Compose exited, stdout/stderr follows")

    stdout = p.stdout.decode("utf-8")
    stderr = p.stderr.decode("utf-8")

    logger.info(f"{stdout=}")
    logger.info(f"{stderr=}")

    # Write its stdout to payload-logs.txt
    with open(stdout_file, "a") as fp:
        fp.write(stdout)
        fp.write(stderr)

    # Copy out the container's payload and agent_cfg.json
    logger.info("Copying inner container results out")
    for file in copy_out:
        logger.info(f"Copying {file} with docker cp, stdout/stderr follows")
        p = subprocess.run(
            shlex.split(f"docker cp {container_name}:/app/{file} ./{file}"),
            capture_output=True,
        )
        logger.info(f"{p.stdout=} {p.stderr=}")

    # Destroy the container and associated image
    folder_name = Path(".").resolve().name
    image_name = f"{folder_name}-{container_name}"
    logger.info(f"Destroying container {container_name} and {image_name}")
    # subprocess.run(shlex.split(f"docker rm {container_name}"))
    # subprocess.run(shlex.split(f"docker image rm {image_name} -f"))
