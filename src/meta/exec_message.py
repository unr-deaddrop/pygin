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
import json
import logging
import sys

from deaddrop_meta.interface_lib import MessagingObject
from deaddrop_meta.protocol_lib import DeadDropMessage
from src.agent_code import message_dispatch
from src.agent_code.config import PyginConfig

from pydantic import TypeAdapter

# import redis

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
MESSAGE_CONFIG_NAME = "message_config.json"
PROTOCOL_STATE_NAME = "protocol_state.json"
MESSAGE_INPUT_NAME = "message.json"
MESSAGE_OUTPUT_NAME = "messages.json"


def select_protocol(msg_cfg: MessagingObject, cfg_obj: PyginConfig) -> str:
    if msg_cfg.server_config.action == "send":
        return cfg_obj.INCOMING_PROTOCOLS[0]
    elif msg_cfg.server_config.action == "receive":
        return cfg_obj.SENDING_PROTOCOL

    raise RuntimeError(f"Unsupported action {msg_cfg.server_config.action}")


def translate_config(msg_cfg: MessagingObject) -> PyginConfig:
    """
    Create a new PyginConfig object suitable for passing into the message
    dispatch unit *as if* it were built for the server.
    """
    # Construct PyginConfig
    cfg_obj = PyginConfig.from_msg_obj(msg_cfg)

    # Select desired protocol. In our case, we completely ignore the preferred
    # protocol set in msg_cfg, because Pygin is only configured to listen/send
    # over a fixed set of protocols.
    #
    # When sending messages, the first configured protocol used for receiving
    # is selected. When receiving messages, the protocol specified in
    # SENDING_PROTOCOL is used.
    #
    # FIXME: Note that this means that heartbeats and logs, if different
    # from SENDING_PROTOCOL, will be lost! This will need to be resolved later.
    # In an ideal world, they'd both accept lists, where the order signifies
    # priority; if a message fails to send on one protocol, you go to the next.
    # Exhaust all the protocols, and that's a failure. However, this is logic
    # more complex than what we're prepared to handle right now, so I'm going
    # to make this assumption and run with it.
    protocol_name = select_protocol(msg_cfg, cfg_obj)

    if not protocol_name:
        raise RuntimeError("Could not resolve a protocol name, was one configured?")

    proto_cfg = cfg_obj.protocol_configuration[protocol_name].convert_to_server_config(
        msg_cfg.endpoint_model_data
    )
    cfg_obj.protocol_configuration[protocol_name] = proto_cfg
    return cfg_obj


def send_message(msg_cfg: MessagingObject, msg: DeadDropMessage) -> dict[str, Any]:
    """
    Send a message through the command dispatch unit.
    """
    # Invoke translator, returns protocol config
    cfg_obj = translate_config(msg_cfg)

    # Invoke message dispatch unit, and return whatever it returns
    protocol_name = select_protocol(msg_cfg, cfg_obj)
    return message_dispatch.send_message(msg, protocol_name, cfg_obj)


def receive_msgs(msg_cfg: MessagingObject) -> list[DeadDropMessage]:
    """
    Receive messages through the command dispatch unit.

    Note that it is up to the server to drop duplicate messages as needed. With
    the exception of certain protocols, no effort is made to keep track of messages
    that have already been seen.
    """
    # Invoke translator, returns dict suitable as input to the function as-is
    cfg_obj = translate_config(msg_cfg)

    # Create new Redis connection (should be valid on the Python implementation
    # of the DeadDrop server, when containerized). Do not use decode_responses=True,
    # since this assumption is not used internally.
    #
    # FIXME: Since they operate in different Compose stacks, the "redis" container
    # is unfortunately unavailable to the agent, so we can't do this after all..
    # we might have to revisit (e.g. making the network bridged)
    # redis_con = redis.Redis(host="redis", port=6379, decode_responses=False)
    redis_con = None

    # Invoke message dispatch unit, and return whatever it returns
    protocol_name = select_protocol(msg_cfg, cfg_obj)
    target_id = msg_cfg.server_config.listen_for_id
    all_msgs = []
    while True:
        new_msgs = message_dispatch.retrieve_new_messages(
            protocol_name, cfg_obj, redis_con
        )
        all_msgs += new_msgs
        if target_id and target_id not in [msg.message_id for msg in new_msgs]:
            # If we're looking for a specific message, continue retrying until we
            # see it, but *don't* drop any messages we do see in the meantime.
            # Celery will time us out if this takes too long, anyways.
            logger.info(f"Did not see desired command response, retrying ({new_msgs=})")
        else:
            break

    return all_msgs


if __name__ == "__main__":
    # Get message_config.json, convert to MessagingObject
    if not Path(MESSAGE_CONFIG_NAME).exists():
        raise RuntimeError(f"Missing {MESSAGE_CONFIG_NAME}!")

    with open(MESSAGE_CONFIG_NAME, "rt") as fp:
        msg_cfg = MessagingObject.model_validate_json(fp.read())

    # Select the correct function to invoke
    if msg_cfg.server_config.action == "send":
        # Get message and send
        if not Path(MESSAGE_INPUT_NAME).exists():
            raise RuntimeError(f"Missing {MESSAGE_INPUT_NAME} to send!")

        with open(MESSAGE_INPUT_NAME, "rt") as fp:
            msg = DeadDropMessage.model_validate_json(fp.read())

        send_message(msg_cfg, msg)
    elif msg_cfg.server_config.action == "receive":
        # Receive messages and serialize to JSON
        result = receive_msgs(msg_cfg)

        ta = TypeAdapter(list[DeadDropMessage])
        with open(MESSAGE_OUTPUT_NAME, "wb+") as fp2:
            # Note this returns bytes, not str, so we open the file as binary
            fp2.write(ta.dump_json(result))
    else:
        raise RuntimeError(f"Unknown action {msg_cfg.server_config.action}")

    # Write out the updated protocol state from MessagingObject
    with open(PROTOCOL_STATE_NAME, "wt+") as fp:
        json.dump(msg_cfg.protocol_state, fp)
