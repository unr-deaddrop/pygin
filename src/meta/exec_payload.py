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

logging.basicConfig(
    handlers=[
        logging.FileHandler("payload-logs.txt", mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
    level=logging.DEBUG,
    format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

RANDOM_CHARSET = string.ascii_lowercase + string.digits

if __name__ == "__main__":
    logger.info("Overwriting docker-compose-payload.yml")
    with open("docker-compose-payload.yml") as fp:
        data: dict[str, Any] = yaml.safe_load(fp)
    
    # Generate a random container name with reasonably low collision chance
    # https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits
    container_name = "".join([random.choice(RANDOM_CHARSET) for _ in range(16)])
    logger.info(f"Selected {container_name=}")
    
    # Overwrite the service and container names accordingly
    data['services']['pygin_build']['container_name'] = container_name
    data['services'][container_name] = data['services'].pop('pygin_build')
    
    # Rewrite the file
    with open("docker-compose-payload.yml", "wt+") as fp:
        yaml.dump(data, fp)
    
    # Run Docker Compose to completion, capturing its output (this avoids having
    # to manually hunt down the logs or redirecting the output in other ways)
    logger.info("Starting Docker Compose")
    command = shlex.split("docker compose -f docker-compose-payload.yml up")
    p = subprocess.run(command, capture_output=True)
    logger.info("Docker Compose exited")
    
    # Write its stdout to payload-logs.txt
    with open("payload-logs.txt", "a") as fp:
        fp.write(p.stdout.decode('utf-8'))
        
    # Copy out the container's payload and agent_cfg.json
    logger.info("Copying inner container results out")
    subprocess.run(shlex.split(f"docker cp {container_name}:/app/agent_cfg.json ./agent_cfg.json"))
    subprocess.run(shlex.split(f"docker cp {container_name}:/app/payload.zip ./payload.zip"))
    
    # Destroy the container and associated image
    folder_name = Path(".").resolve().name
    image_name = f"{folder_name}-{container_name}"
    logger.info(f"Destroying container {container_name} and {image_name}")
    subprocess.run(shlex.split(f"docker rm {container_name}"))
    subprocess.run(shlex.split(f"docker image rm {image_name} -f"))
    
    
    
    