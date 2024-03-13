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
from deaddrop_meta.interface_lib import MessagingObject
from deaddrop_meta.protocol_lib import DeadDropMessage

def send_message(msg_cfg: MessagingObject, msg: DeadDropMessage) -> dict[str, Any]:
    raise NotImplementedError

def receive_msgs(msg_cfg: MessagingObject) -> list[DeadDropMessage]:
    raise NotImplementedError

if __name__ == "__main__":
    # Do stuff with the message_config.json and the message.json
    raise NotImplementedError