"""
The script entrypoint for the server's messaging system.

This operates by spinning up a container in which all of the agent's 
messaging modules are available with dependencies involved, then passing
in the normal arguments for that protocol as if it were called from the
message dispatch unit.

Currently, Pygin specifies that it listens over multiple protocols for
receiving messages, but only issues messages over a specific protocol.
In both cases, it is assumed that the user has chosen a valid protocol
in ServerMessagingData.
"""

from pathlib import Path
import logging
import sys

from src.meta._exec_shared import run_compose_file

# The Docker compose file to invoke.
DOCKER_COMPOSE_FILE = Path("docker-compose-messaging.yml")

# Where to write the stdout of the Docker Compose environment to.
LOG_OUTPUT = Path("message-logs.txt")

# The name of the Docker Compose service to overwrite.
DOCKER_COMPOSE_SERVICE = "pygin_message"

# The files to copy out of the container (noting that message-logs.txt exists
# on the server's container already, so no need to copy it out)
COPY_OUT = ["messages.json", "protocol_state.json"]

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


# Log uncaught excepptions
# https://stackoverflow.com/questions/6234405/logging-uncaught-exceptions-in-python
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception

if __name__ == "__main__":
    run_compose_file(DOCKER_COMPOSE_FILE, DOCKER_COMPOSE_SERVICE, LOG_OUTPUT, COPY_OUT)
