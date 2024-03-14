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

Each protocol specifies its own translator. 

TODO: How do we expose these translators?
"""
from typing import Any

from deaddrop_meta.interface_lib import MessagingObject
from deaddrop_meta.protocol_lib import DeadDropMessage
from src.agent_code import message_dispatch
from src.agent_code.config import PyginConfig

def translate_config(msg_cfg: MessagingObject) -> dict[str, Any]:
    # Construct PyginConfig
    
    # Select desired protocol
    
    # Get PyginConfig to ProtocolConfig to dict translator
    
    # Invoke translator, returns dict suitable as input to the function as-is
    raise RuntimeError

def send_message(msg_cfg: MessagingObject, msg: DeadDropMessage) -> dict[str, Any]:
    """
    Send a message through the command dispatch unit.
    """    
    # Invoke translator, returns dict suitable as input to the function as-is
    
    # Invoke message dispatch unit (we don't have a Redis connection, we'll
    # probably have to make it optional? the alternative is to do protocol lookup
    # ourself)
    
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
    
    # Invoke message dispatch unit (we don't have a Redis connection, we'll
    # probably have to make it optional? the alternative is to do protocol lookup
    # ourself)
    
    # Return whatever the relevant protocol class returns
    raise NotImplementedError

if __name__ == "__main__":
    # Get message_config.json, convert to MessagingObject
    
    # Get message.json if present, convert to msg
    
    # Select the correct function to invoke
    
    # If receiving messages, write out the messages as messages.json
    
    # Write out the resulting MessagingObject with updated protocol state,
    # if needed
    raise NotImplementedError