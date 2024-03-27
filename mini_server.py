"""
Simple server that adheres to the DeadDrop protocol and can be used to
manually send messages to the agent without needing to set up the backend
yourself.
"""

# region imports
from pathlib import Path
from typing import Any
import base64
import datetime
import json
import logging
import time
import sys

from deaddrop_meta.protocol_lib import (
    DeadDropMessage,
    DeadDropMessageType,
    CommandRequestPayload,
    CommandResponsePayload,
)
from deaddrop_meta.interface_lib import (
    MessagingObject,
    EndpointMessagingData,
    ServerMessagingData,
)

# Make all protocols visible so that PyginConfig works correctly
from src.protocols import *  # noqa: F401, F403

# Make the server entrypoint visible
from src.meta import exec_message as messaging

logging.basicConfig(
    handlers=[logging.StreamHandler(sys.stdout)],
    level=logging.DEBUG,
    format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()
# endregion

# Endpoint configuration, normally stored by the server. Corresponds to the Endpoint
# model in Django.
ENDPOINT_NAME = "my_endpoint"
ENDPOINT_HOSTNAME = "my_hostname"
ENDPOINT_ADDRESS = "127.0.0.1"

# Either a base64-encoded PEM Ed25519 key, or None.
SERVER_PRIVATE_KEY = "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSU1qdnhsSEUzcTFKVEZYQ0RnMG1lVGxpSXIyRGgxdDB4Q2xkLzZXMmp5ZC8KLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQ=="

# The command to issue (this is protocol independent)

# CMD_NAME: str = "ping"
# CMD_ARGS: dict[str, Any] = {
#     "message": "test",
#     "ping_timestamp": datetime.utcnow().timestamp(),
# }
CMD_NAME: str = "shell"
CMD_ARGS: dict[str, Any] = {
    "command": "cat Makefile",
    "use_shell": True,
}
# CMD_NAME: str = "empyrean_exec"
# CMD_ARGS: dict[str, Any] = {}

# Path to agent_cfg.json. Note that the selected protocol is derived
# from this file, consistent with how the server/agent currently interacts.
# It's assumed that this agent configuration is what you're currently running.

if __name__ == "__main__":
    # Load configuration
    with open(Path("./agent_cfg.json"), "rt") as fp:
        cfg = json.load(fp)

    # Construct the command_request message
    msg = DeadDropMessage(
        destination_id=cfg["agent_config"]["AGENT_ID"],
        payload=CommandRequestPayload(
            message_type=DeadDropMessageType.CMD_REQUEST,
            cmd_name=CMD_NAME,
            cmd_args=CMD_ARGS,
        ),
    )
    print(msg.model_dump_json())

    # Construct messaging object - note that we don't have any sort
    # of state management, so the protocol state dict is empty. The rest
    # of this is identical to the backend implementation.
    msg_obj = MessagingObject(
        agent_config=cfg["agent_config"],
        protocol_config=cfg["protocol_config"],
        protocol_state={},
        endpoint_model_data=EndpointMessagingData(
            name=ENDPOINT_NAME, hostname=ENDPOINT_HOSTNAME, address=ENDPOINT_ADDRESS
        ),
        server_config=ServerMessagingData(
            action="send",
            listen_for_id=None,
            server_private_key=base64.b64decode(SERVER_PRIVATE_KEY),
            preferred_protocol=None,
        ),
    )

    # Invoke server-side entrypoint
    messaging.send_message(msg_obj, msg)

    recv_msg_obj = MessagingObject(
        agent_config=cfg["agent_config"],
        protocol_config=cfg["protocol_config"],
        protocol_state={},
        endpoint_model_data=EndpointMessagingData(
            name=ENDPOINT_NAME, hostname=ENDPOINT_HOSTNAME, address=ENDPOINT_ADDRESS
        ),
        server_config=ServerMessagingData(
            action="receive",
            listen_for_id=msg.message_id,
            server_private_key=None,
            preferred_protocol=None,
        ),
    )

    # Read back all messages being sent by the server, then select just the
    # response to our message (if multiple messages exist)
    while True:
        time.sleep(1)

        logger.info("Waiting for response...")
        recv_msgs = messaging.receive_msgs(recv_msg_obj)

        logger.info(
            f"Got the following message ids back: {[msg.message_id for msg in recv_msgs]}"
        )

        for recv_msg in recv_msgs:
            if not isinstance(recv_msg.payload, CommandResponsePayload):
                continue

            payload: CommandResponsePayload = recv_msg.payload
            if payload.request_id != msg.message_id:
                continue

            logger.info(f"Got response to original message: {recv_msg}")

            # Only if ping was used
            if CMD_NAME == "ping":
                start_time: datetime.datetime = payload.result["ping_timestamp"]
                end_time: datetime.datetime = payload.result["pong_timestamp"]
                return_time = datetime.datetime.now(datetime.UTC)
                logger.info(
                    f"The ping time was {(end_time-start_time).total_seconds():.2f} seconds to receive, {(return_time-start_time).total_seconds():.2f} seconds RTT"
                )

            exit()
