"""
Entrypoint for generating a payload from the server's container.
"""
import logging
import sys

from src.meta._exec_shared import run_compose_file

# The Docker compose file to invoke.
DOCKER_COMPOSE_FILE = "docker-compose-payload.yml"

# Where to write the stdout of the Docker Compose environment to.
LOG_OUTPUT = "payload-logs.txt"

# The name of the Docker Compose service to overwrite.
DOCKER_COMPOSE_SERVICE = "pygin_build"

# The files to copy out of the container.
COPY_OUT = [
    "agent_cfg.json",
    "payload.zip"
]

logging.basicConfig(
    handlers=[
        logging.FileHandler(LOG_OUTPUT, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
    level=logging.DEBUG,
    format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    run_compose_file(DOCKER_COMPOSE_FILE, DOCKER_COMPOSE_SERVICE, LOG_OUTPUT, COPY_OUT)
