"""
This implements the messaging dispatch module as described in DeadDrop's
generic architecture model for agents.

If any additional operations are needed before handing the message off to
a particular protocol, it should be done here. This may include adding 
protocol-specific arguments that are not already present in the configuration
object, and therefore must be handled on a case-by-case basis. 

The spirit of this design is that any edge case handling can be centralized
to this module, allowing the protocols to remain (relatively) loosely bound
from the rest of Pygin's libraries.
"""

from typing import Any, Type
import logging

import redis


# Make all protocols visible. This is an intentional star-import so that
# our helper functions work.
from src.protocols import *  # noqa: F401,F403

from src.agent_code import config
from src.protocols._shared_lib import PyginMessage
from src.libs import protocol_lib

logger = logging.getLogger(__name__)


def retrieve_new_messages(
    protocol_name: str,
    cfg: config.PyginConfig,
    redis_con: redis.Redis,
    drop_seen: bool = True,
) -> list[PyginMessage]:
    """
    Retrieve all new messages over the specified service.

    This function searches for the associated protocol handler (a subclass of
    `ProtocolBase`) and asks it to retrieve all messages from the service. Protocol
    handlers may store state information in the Redis database passed into this
    function; for example, a YouTube-based service may store the upload date of
    the most recent message seen.

    This function also keeps track of the message IDs of all messages seen, and
    by default will explicitly drop any messages that have already been recorded
    by this function. Even when disabled, this function will log duplicate messages.

    :param protocol_name: The name of the protocol to retrieve messages from.
    :param cfg: The Pygin configuration object, which may also contain static
        configuration for the underlying protocols.
    :param redis_con: A Redis connection, typically `app.backend.client` when
        invoked from Celery's tasking module.
    :param drop_seen: Whether to drop any messages with IDs that have already
        been seen, as stored by the Redis database.
    """
    result: list[PyginMessage] = []
    
    # Get a handle to the relevant protocol class, if it exists. Parse the arguments
    # accordingly from the PyginConfig class.
    protocol_class = protocol_lib.lookup_protocol(protocol_name)

    protocol_parser_type: Type[protocol_lib.ProtocolArgumentParser] = protocol_class.config_parser
    protocol_parser = protocol_parser_type.from_config_obj(cfg.protocol_configuration[protocol_name])
    protocol_args = protocol_parser.get_stored_args()

    # Invoke the protocol's message retrieval function. At this point, any protocol-specific
    # arguments are added in by the message dispatch unit, such as the inclusion of 
    # a handle to the Redis database in the keyword arguments.
    #
    # XXX: I'm holding off on this for now. This should probably call another function
    # that adds more arguments as needed, then combines the protocol_args dictionary
    # with our new dictionary containing runtime arguments.
    new_msgs = protocol_class.get_new_messages(protocol_args)


    # For each message, check if was already seen and act accordingly based on
    # `drop_seen`. In all cases, add message IDs to the set.
    for msg in new_msgs:
        # String comparisons to UUIDs don't work as expected, so you have
        # to explicitly convert a uuid.UUID to a string for it to work with
        # the strings contained in the Redis database
        msg_id = str(msg.message_id)
        
        # TODO: This wasn't working earlier because Redis likes returning things as
        # bytes, not str. 
        if redis_con.sismember(cfg.REDIS_MESSAGES_SEEN_KEY, msg_id):
            logger.debug(f"Duplicate message {msg_id} seen by message dispatch unit")
            if drop_seen:
                logger.debug(f"Dropping duplicate message {msg_id}")
                continue
            
            # Add this new message to the set
            redis_con.sadd(cfg.REDIS_MESSAGES_SEEN_KEY, msg_id)
        
        result.append(msg)

    # Return the remaining set of messages.
    return result


def send_message(
    msg: PyginMessage,
    protocol_name: str,
    cfg: config.PyginConfig,
) -> dict[str, Any]:
    """
    Send a message over the specified protocol.
    """
    # Sign the message
    # TODO: implement

    # Get a handle to the relevant protocol class, if it exists. Parse the arguments
    # accordingly from the PyginConfig class.
    # TODO: if this is such a common operation, shouldn't protocols just define a default
    # "parse config object and get dictionary of arguments" operation?
    protocol_class = protocol_lib.lookup_protocol(protocol_name)

    protocol_parser_type: Type[protocol_lib.ProtocolArgumentParser] = protocol_class.config_parser
    protocol_parser = protocol_parser_type.from_config_obj(cfg.protocol_configuration[protocol_name])
    protocol_args = protocol_parser.get_stored_args()

    # Invoke the protocol's message sending function. Again, pass in the Redis
    # connection as a keyword argument; it's up to the protocol whether or not
    # to use this for any state management. Directly return the result; any error
    # handling or message re-sending must occur at the protocol level.
    return protocol_class.send_msg(msg, protocol_args)
