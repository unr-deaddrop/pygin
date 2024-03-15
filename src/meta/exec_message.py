"""
The in-container entrypoint for sending messages.

At this point, it is assumed that a message_config.json exists, and if
a message is being sent, that a message.json exists. These are parsed
accordingly.

This works in a pretty simple manner.
- The entire MessagingObject is loaded as a PyginConfig object, with additional
  keys set (such as the server's private key) that are not normally included
  in agent_cfg.json.
- For the desired protocol, a translator is invoked that converts the relevant
  "agent-side" PyginConfig.protocol_config elements into "server-side" config.
- The message dispatch unit is invoked with the modified configuration.

Each protocol specifies its own translator, as provided in its ProtocolConfig
object.
"""

from pathlib import Path
from typing import Any
import logging
import sys

from deaddrop_meta.interface_lib import MessagingObject
from deaddrop_meta.protocol_lib import DeadDropMessage
from src.agent_code import message_dispatch
from src.agent_code.config import PyginConfig

logging.basicConfig(
    handlers=[
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

LOG_FILE_NAME = "message-logs.txt"
PROTOCOL_STATE_NAME = "protocol_state.json"
MESSAGE_OUTPUT_NAME = "messages.json"


def translate_config(msg_cfg: MessagingObject) -> dict[str, Any]:
    # Construct PyginConfig

    # Select desired protocol

    # Get PyginConfig to ProtocolConfig to dict translator

    # Invoke translator, returns dict suitable as input to the function as-is
    raise NotImplementedError


def send_message(msg_cfg: MessagingObject, msg: DeadDropMessage) -> dict[str, Any]:
    """
    Send a message through the command dispatch unit.
    """
    # Invoke translator, returns dict suitable as input to the function as-is

    # Invoke message dispatch unit (should we just use the already available
    # Redis service that the server uses? we're assuming that Celery is in use,
    # so it *is* available for message checking if needed)

    # Return whatever the relevant protocol class returns

    raise NotImplementedError


def receive_msgs(msg_cfg: MessagingObject) -> list[DeadDropMessage]:
    """
    Receive messages through the command dispatch unit.

    Note that it is up to the server to drop duplicate messages as needed. With
    the exception of certain protocols, no effort is made to keep track of messages
    that have already been seen.
    """
    # Invoke translator, returns dict suitable as input to the function as-is

    # Invoke message dispatch unit (should we just use the already available
    # Redis service that the server uses? we're assuming that Celery is in use,
    # so it *is* available for message checking if needed)

    # Return whatever the relevant protocol class returns
    raise NotImplementedError


if __name__ == "__main__":
    # Get message_config.json, convert to MessagingObject

    # Get message.json if present, convert to msg

    # Select the correct function to invoke

    # If receiving messages, write out the messages as messages.json

    # Write out the updated protocol state from MessagingObject if needed
    # TODO: Not currently supported, because nothing uses this
    raise NotImplementedError
