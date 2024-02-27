"""
Simple server that adheres to the DeadDrop protocol and can be used to
manually send messages to the agent.

This is currently hardcoded for Pygin's dddb_local protocol, since it's
reliable and won't randomly explode (and won't cause any ToS violations).
"""

from pathlib import Path
from typing import Type, Any

from src.libs.protocol_lib import DeadDropMessage, DeadDropMessageType, ProtocolArgumentParser, get_protocols_as_dict
from src.agent_code.config import PyginConfig

# Make all protocols visible so that PyginConfig works correctly
from src.protocols import *
from src.protocols.dddb_local import dddbLocalConfig

# The command to issue
CMD_NAME: str = "ping"
CMD_ARGS: dict[str, str] =  {
    "message": "test"
}

def switch_inbox_outbox(cfg: PyginConfig) -> None:
    """
    Switch the inbox and outbox fields for the dddb_local configuration.
    """
    protocol_cfg: dddbLocalConfig = cfg.protocol_configuration["dddb_local"]
    temp = protocol_cfg.DDDB_LOCAL_INBOX_DIR
    protocol_cfg.DDDB_LOCAL_INBOX_DIR = protocol_cfg.DDDB_LOCAL_OUTBOX_DIR
    protocol_cfg.DDDB_LOCAL_OUTBOX_DIR = temp

def get_dddb_local_args(cfg: PyginConfig) -> dict[str, Any]:
    """
    Get the arguments for the dddb_local protocol. dddb_local operates
    entirely on the configuration and doesn't (shouldn't) require any
    additional information, at least for right now.
    
    Note this doesn't switch the inbox/outbox for the protocol, since doing
    it twice will just revert the operation!
    """
    dddb_local_protocol = get_protocols_as_dict()["dddb_local"]
    argparser: Type[ProtocolArgumentParser] = dddb_local_protocol.config_parser
    argparser.from_config_obj(cfg.protocol_configuration["dddb_local"])
    
    return argparser.get_stored_args()

def send_over_dddb_local(msg: DeadDropMessage, cfg: PyginConfig):
    args = get_dddb_local_args(cfg)
    dddb_local_protocol = get_protocols_as_dict()["dddb_local"]
    dddb_local_protocol.send_msg(msg, args)
    
def receive_all_over_dddb_local(cfg: PyginConfig) -> list[DeadDropMessage]:
    args = get_dddb_local_args(cfg)
    dddb_local_protocol = get_protocols_as_dict()["dddb_local"]
    return dddb_local_protocol.get_new_messages(args)
    

if __name__ == "__main__":
    # Load configuration
    cfg = PyginConfig.from_cfg_file(Path('./agent.cfg'))    
    
    # Construct the command_request message
    msg = DeadDropMessage(
        message_type = DeadDropMessageType.CMD_REQUEST,
        payload = {
            "cmd_name": CMD_NAME,
            "cmd_args": CMD_ARGS
        }
    )
    
    # Fire off message using Pygin's built-in protocol library, sending it
    # to the inbox as defined by the dddb protocol config (by setting the
    # outbox to the inbox)
    switch_inbox_outbox(cfg)
    send_over_dddb_local(msg, cfg)
    
    # Read back all messages from the outbox and select the response to
    # our original message
    print(receive_all_over_dddb_local(cfg))
    
    
    
    