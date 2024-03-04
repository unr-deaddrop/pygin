"""
Simple server that adheres to the DeadDrop protocol and can be used to
manually send messages to the agent.

This is currently hardcoded for Pygin's local protocols, since it's
reliable and won't randomly explode (and won't cause any ToS violations).
"""

from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from pprint import pprint
from typing import Type, Any, Callable
import logging
import time
import sys

from deaddrop_meta.protocol_lib import (
    DeadDropMessage,
    DeadDropMessageType,
    ProtocolArgumentParser,
    get_protocols_as_dict,
)
from src.agent_code.config import PyginConfig

# Make all protocols visible so that PyginConfig works correctly
from src.protocols import *
from src.protocols.plaintext_local import PlaintextLocalConfig
from src.protocols.plaintext_tcp import PlaintextTCPConfig

logging.basicConfig(
    handlers=[logging.StreamHandler(sys.stdout)],
    level=logging.DEBUG,
    format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()

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


# currently either plaintext_tcp or plaintext_local
SELECTED_PROTOCOL = "plaintext_tcp"


@dataclass
class ProtocolEntrypoints:
    send_msg: Callable[[DeadDropMessage, PyginConfig], None]
    recv_msg: Callable[[PyginConfig], list[DeadDropMessage]]


def switch_inbox_outbox(cfg: PyginConfig) -> None:
    """
    Switch the inbox and outbox fields for the plaintext_local configuration.
    """
    protocol_cfg: PlaintextLocalConfig = cfg.protocol_configuration["plaintext_local"]
    temp = protocol_cfg.PLAINTEXT_LOCAL_INBOX_DIR
    protocol_cfg.PLAINTEXT_LOCAL_INBOX_DIR = protocol_cfg.PLAINTEXT_LOCAL_OUTBOX_DIR
    protocol_cfg.PLAINTEXT_LOCAL_OUTBOX_DIR = temp


def set_ports(cfg: PyginConfig, recv_port: int, send_port: int) -> None:
    """
    Set the receiving and sending ports for the plaintext_tcp configuration.
    """
    protocol_cfg: PlaintextTCPConfig = cfg.protocol_configuration["plaintext_tcp"]
    protocol_cfg.PLAINTEXT_TCP_LISTEN_RECV_PORT = recv_port
    protocol_cfg.PLAINTEXT_TCP_SEND_PORT = send_port


def get_plaintext_local_args(cfg: PyginConfig) -> dict[str, Any]:
    """
    Get the arguments for the plaintext_tcp protocol. plaintext_tcp operates
    entirely on the configuration and doesn't (shouldn't) require any
    additional information, at least for right now.

    Note this doesn't switch the inbox/outbox for the protocol, since doing
    it twice will just revert the operation!
    """
    plaintext_local_protocol = get_protocols_as_dict()["plaintext_local"]
    argparser: Type[ProtocolArgumentParser] = plaintext_local_protocol.config_parser
    p = argparser.from_config_obj(cfg.protocol_configuration["plaintext_local"])

    return p.get_stored_args()


def get_plaintext_tcp_args(cfg: PyginConfig) -> dict[str, Any]:
    """
    Get the arguments for the plaintext_tcp protocol. Like plaintext_tcp,
    there's no extra argument processing needed, so it's sufficient to just shove
    everything through the config parser and call it a day.
    """
    plaintext_tcp_protocol = get_protocols_as_dict()["plaintext_tcp"]
    argparser: Type[ProtocolArgumentParser] = plaintext_tcp_protocol.config_parser
    p = argparser.from_config_obj(cfg.protocol_configuration["plaintext_tcp"])

    return p.get_stored_args()


def send_over_plaintext_local(msg: DeadDropMessage, cfg: PyginConfig):
    args = get_plaintext_local_args(cfg)
    plaintext_local_protocol = get_protocols_as_dict()["plaintext_local"]
    plaintext_local_protocol.send_msg(msg, args)


def receive_all_over_plaintext_local(cfg: PyginConfig) -> list[DeadDropMessage]:
    args = get_plaintext_local_args(cfg)
    plaintext_local_protocol = get_protocols_as_dict()["plaintext_local"]
    return plaintext_local_protocol.get_new_messages(args)


def send_plaintext_entrypoint(msg: DeadDropMessage, cfg: PyginConfig):
    # Fire off message using Pygin's built-in protocol library, sending it
    # to the inbox as defined by the dddb protocol config (by setting the
    # outbox to the inbox)
    switch_inbox_outbox(cfg)
    send_over_plaintext_local(msg, cfg)


def receive_plaintext_entrypoint(cfg: PyginConfig) -> list[DeadDropMessage]:
    return receive_all_over_plaintext_local(cfg)


def send_tcp_entrypoint(msg: DeadDropMessage, cfg: PyginConfig):
    # Make a deep copy of the agent's configuration model.
    cfg = cfg.model_copy(deep=True)
    protocol_cfg: PlaintextTCPConfig = cfg.protocol_configuration["plaintext_tcp"]
    
    # The agent always uses the listener to receive messages, so we send messages
    # by instantiating a connection, using the specified receiver host/port
    # as the send port.
    protocol_cfg.PLAINTEXT_TCP_USE_LISTENER_TO_SEND = False
    # Host is always localhost, whether it's Docker or not.
    protocol_cfg.PLAINTEXT_TCP_INITIATE_SEND_HOST = "localhost"
    protocol_cfg.PLAINTEXT_TCP_INITIATE_SEND_PORT = protocol_cfg.PLAINTEXT_TCP_LISTEN_RECV_PORT
    args = get_plaintext_tcp_args(cfg)
    
    plaintext_tcp_protocol = get_protocols_as_dict()["plaintext_tcp"]
    plaintext_tcp_protocol.send_msg(msg, args)


def receive_tcp_entrypoint(cfg: PyginConfig) -> list[DeadDropMessage]:
    # Make a deep copy of the agent's configuration model.
    cfg = cfg.model_copy(deep=True)
    protocol_cfg: PlaintextTCPConfig = cfg.protocol_configuration["plaintext_tcp"]
    plaintext_tcp_protocol = get_protocols_as_dict()["plaintext_tcp"]
    
    # If the agent has been configured to initiate connections to send messages, 
    # we can use the built-in listener to get new messages. 
    if not protocol_cfg.PLAINTEXT_TCP_USE_LISTENER_TO_SEND:
        protocol_cfg.PLAINTEXT_TCP_LISTEN_BIND_HOST = protocol_cfg.PLAINTEXT_TCP_INITIATE_SEND_HOST
        protocol_cfg.PLAINTEXT_TCP_LISTEN_RECV_PORT = protocol_cfg.PLAINTEXT_TCP_INITIATE_SEND_PORT
        args = get_plaintext_tcp_args(cfg)
        return plaintext_tcp_protocol.get_new_messages(args)    
    
    # If the agent has been configured to listen for connections before sending
    # the connection a message, do this instead.
    protocol_cfg.PLAINTEXT_TCP_INITIATE_RECV_HOST = protocol_cfg.PLAINTEXT_TCP_INITIATE_SEND_HOST
    protocol_cfg.PLAINTEXT_TCP_INITIATE_RECV_PORT = protocol_cfg.PLAINTEXT_TCP_INITIATE_SEND_PORT
    args = get_plaintext_tcp_args(cfg)
    return plaintext_tcp_protocol.recv_msg_by_initiating(args)


PROTOCOL_ENTRYPOINTS: dict[str, ProtocolEntrypoints] = {
    "plaintext_local": ProtocolEntrypoints(
        send_plaintext_entrypoint, receive_plaintext_entrypoint
    ),
    "plaintext_tcp": ProtocolEntrypoints(send_tcp_entrypoint, receive_tcp_entrypoint),
}

if __name__ == "__main__":
    # Load configuration
    cfg = PyginConfig.from_cfg_file(Path("./agent.cfg"))

    # Construct the command_request message
    msg = DeadDropMessage(
        message_type=DeadDropMessageType.CMD_REQUEST,
        payload={
            "cmd_name": CMD_NAME,
            "cmd_args": CMD_ARGS,
        },
    )

    # Select protocol functions
    if SELECTED_PROTOCOL not in PROTOCOL_ENTRYPOINTS:
        raise RuntimeError(f"{SELECTED_PROTOCOL} not supported!")
    protocol = PROTOCOL_ENTRYPOINTS[SELECTED_PROTOCOL]

    # Send message
    protocol.send_msg(msg, cfg)

    # Read back all messages being sent by the server, then select just the
    # response to our message (if multiple messages exist)
    while True:
        time.sleep(1)

        logger.info("Waiting for response...")
        recv_msgs = protocol.recv_msg(cfg)

        logger.info(
            f"Got the following message ids back: {[msg.message_id for msg in recv_msgs]}"
        )

        for recv_msg in recv_msgs:
            if "request_id" in recv_msg.payload and recv_msg.payload[
                "request_id"
            ] == str(msg.message_id):
                logger.info(f"Got response to original message: {recv_msg}")

                # Only if ping was used
                if CMD_NAME == "ping":
                    start_time = float(recv_msg.payload["result"]["ping_timestamp"])
                    end_time = float(recv_msg.payload["result"]["pong_timestamp"])
                    return_time = datetime.utcnow().timestamp()
                    logger.info(
                        f"The ping time was {end_time-start_time:.2f} seconds to receive, {return_time-start_time:.2f} seconds RTT"
                    )
                
                exit()