"""
This implements the messaging dispatch module as described in DeadDrop's
generic architecture model for agents.
"""

from typing import Any

import redis

# Make all protocols visible. This is an intentional star-import so that
# our helper functions work.
from src.protocols import *  # noqa: F401,F403

from src.agent_code import config
from src.protocols._shared_lib import PyginMessage
from src.libs import protocol_lib


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
    # Get a handle to the relevant protocol class, if it exists

    # Invoke the protocol's message retrieval function, passing in the Redis connection
    # as a keyword argument. It's up to the protocol whether or not it actually uses it.

    # Get all previously seen message IDs from the Redis database.

    # For each message, check if was already seen and act accordingly based on
    # `drop_seen`.

    # Return the remaining set of messages.
    raise NotImplementedError


def send_message(
    protocol_name: str,
    cfg: config.PyginConfig,
) -> dict[str, Any]:
    """
    Send a message over the specified protocol.
    """
    # Get a handle to the relevant protocol class, if it exists

    # Invoke the protocol's message sending function. Again, pass in the Redis
    # connection as a keyword argument; it's up to the protocol whether or not
    # to use this for any state management. Directly return the result; any error
    # handling or message re-sending must occur at the protocol level.
    raise NotImplementedError
