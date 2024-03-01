"""
Various routines for generating the agent's metadata.

This covers:
- commands.json, which serves as a reference for the commands this agent
  supports and their arguments
- protocols.json, which exposes the protocols this agent supports and
  the configuration keys specific to those protocols for this agent
- agent.json, which exposes core agent metadata and configurable
  options for the agent itself

These three files are placed in the same folder relative to execution.
It is intended to be executed as `python3 -m src.meta.generate_metadata`
as a standalone script.
"""

from pathlib import Path
import logging
import sys

# Make all protocols and commands visible. This is intentional, as the helper
# functions in the protocol and command libraries depend on their subclasses
# being imported.
from src.protocols import *  # noqa: F403, F401
from src.commands import *  # noqa: F403, F401
from src.libs import protocol_lib, command_lib
from src.meta import agent

# Set up logging
logging.basicConfig(
    handlers=[logging.StreamHandler(sys.stdout)],
    level=logging.DEBUG,
    format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()

COMMAND_FILE = Path("./commands.json")
PROTOCOL_FILE = Path("./protocols.json")
AGENT_FILE = Path("./agent.json")


def generate_command_metadata(filepath_out: Path) -> None:
    command_classes = command_lib.export_all_commands()
    logger.info(f"Exporting {len(command_classes)} command(s)")

    with open(filepath_out, "wt+") as fp:
        fp.write(command_lib.export_commands_as_json(command_classes, indent=4))


def generate_protocol_metadata(filepath_out: Path) -> None:
    protocol_classes = protocol_lib.export_all_protocols()
    logger.info(f"Exporting {len(protocol_classes)} protocols(s)")

    with open(filepath_out, "wt+") as fp:
        fp.write(protocol_lib.export_protocols_as_json(protocol_classes, indent=4))


def generate_agent_metadata(filepath_out: Path) -> None:
    with open(filepath_out, "wt+") as fp:
        fp.write(agent.PyginInfo().to_json(indent=2))


if __name__ == "__main__":
    logger.info("Generating commands.json")
    generate_command_metadata(COMMAND_FILE)
    logger.info("Generating protocols.json")
    generate_protocol_metadata(PROTOCOL_FILE)
    logger.info("Generating agent.json")
    generate_agent_metadata(AGENT_FILE)
