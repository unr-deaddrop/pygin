"""
Static metadata definitions for Pygin.
"""

from typing import Type

from deaddrop_meta.agent_lib import SupportedOSTypes, SupportedProtocols, AgentBase
from deaddrop_meta.argument_lib import ArgumentParser, Argument, ArgumentType


class PyginConfigParser(ArgumentParser):
    # In an ideal world, src.agent_code.config would be the one source of truth.
    # However, the spirit is that the meta library should be completely disconnected
    # from everything else, and the fact is that there's no need for a
    # PyginConfigParser outside of this. Additionally, I'd like to keep the config
    # object relatively simple, and shoehorning the standard types and structure
    # of protocols and commands into PyginConfig didn't seem particularly simple.
    #
    # Note that no parser for each argument is defined since this isn't actually
    # intended for use.
    arguments: list[Argument] = [
        Argument(
            arg_type=ArgumentType.STRING,
            name="AGENT_ID",
            description="The agent's UUID.",
        ),
        Argument(
            arg_type=ArgumentType.FLOAT,
            name="CONTROL_UNIT_THROTTLE_TIME",
            description="The time, in seconds, the control unit should sleep on each cycle.",
            default=2,
        ),
        Argument(
            arg_type=ArgumentType.PATH,
            name="AGENT_PRIVATE_KEY_PATH",
            description="The path to the agent's private key.",
        ),
        Argument(
            arg_type=ArgumentType.PATH,
            name="SERVER_PUBLIC_KEY_PATH",
            description="The path to the agent's public key.",
        ),
        Argument(
            arg_type=ArgumentType.STRING,
            name="ENCRYPTION_KEY",
            description="The agent's symmetric encryption key, base64 encoded.",
        ),
        Argument(
            arg_type=ArgumentType.ITERABLE,
            name="INCOMING_PROTOCOLS",
            description="A list of supported agent names for which periodic listener tasks should be scheduled.",
            is_iterable=True,
        ),
        Argument(
            arg_type=ArgumentType.STRING,
            name="HEARTBEAT_PROTOCOL",
            description="The protocol used to send heartbeats.",
        ),
        Argument(
            arg_type=ArgumentType.STRING,
            name="LOGGING_PROTOCOL",
            description="The protocol used to send log bundles.",
        ),
        Argument(
            arg_type=ArgumentType.STRING,
            name="SENDING_PROTOCOL",
            description="The protocol used to send all other messages.",
        ),
        Argument(
            arg_type=ArgumentType.INTEGER,
            name="LOGGING_INTERVAL",
            description="The frequency, in seconds, with which log bundles should be conditionally sent.",
        ),
        Argument(
            arg_type=ArgumentType.INTEGER,
            name="HEARTBEAT_INTERVAL",
            description="The frequency, in seconds, with which heartbeats should be conditionally sent.",
        ),
        Argument(
            arg_type=ArgumentType.STRING,
            name="REDIS_MESSAGES_SEEN_KEY",
            description="The key used by the message dispatch unit to drop duplicate messages.",
            default="_agent_meta-seen-msgs",
        ),
        Argument(
            arg_type=ArgumentType.STRING,
            name="REDIS_NEW_MESSAGES_KEY",
            description="The key used by the control unit to discover completed message tasking.",
            default="_agent_meta-new-msg-task-ids",
        ),
        Argument(
            arg_type=ArgumentType.STRING,
            name="REDIS_MAIN_PROCESS_MESSAGES_SEEN_KEY",
            description="The key used by the control unit to drop duplicated messages.",
            default="_agent_meta-main-msgs-seen",
        ),
        Argument(
            arg_type=ArgumentType.STRING,
            name="RESULT_RETRIEVAL_REATTEMPT_LIMIT",
            description="The number of times a Celery task may be observed to be pending before dropped.",
            default=5,
        ),
        Argument(
            arg_type=ArgumentType.STRING,
            name="INCOMING_ENCODED_MESSAGE_DIR",
            description="The directory used to store incoming messages before decoding.",
            default="./msgs/incoming_raw",
        ),
        Argument(
            arg_type=ArgumentType.STRING,
            name="INCOMING_DECODED_MESSAGE_DIR",
            description="The directory used to store incoming messages after decoding.",
            default="./msgs/incoming_decoded",
        ),
        Argument(
            arg_type=ArgumentType.STRING,
            name="OUTGOING_DECODED_MESSAGE_DIR",
            description="The directory used to store outgoing messages before encoding.",
            default="./msgs/outgoing_decoded",
        ),
        Argument(
            arg_type=ArgumentType.STRING,
            name="OUTGOING_ENCODED_MESSAGE_DIR",
            description="The directory used to store outgoing messages after encoding.",
            default="./msgs/outgoing_raw",
        ),
        Argument(
            arg_type=ArgumentType.STRING,
            name="LOG_DIR",
            description="Where logs should be stored.",
            default="./logs",
        ),
    ]


class PyginInfo(AgentBase):
    """
    Pygin is the reference implementation of a DeadDrop agent.

    Although written in Python and therefore generally platform-agnostic,
    this depends on Redis as its Celery broker and database. In general,
    this is only available on Linux.
    """

    name: str = "pygin"
    description: str = __doc__
    version: str = "0.0.1"
    author: str = "lgactna"
    source: str = "https://github.com/unr-deaddrop/pygin/"
    supported_operating_systems: list[SupportedOSTypes] = [SupportedOSTypes.LINUX]
    supported_protocols: list[SupportedProtocols] = [
        SupportedProtocols.DDDB_LOCAL,
        SupportedProtocols.DDDB_YOUTUBE,
        SupportedProtocols.PLAINTEXT_LOCAL,
    ]
    config_parser: Type[ArgumentParser] = PyginConfigParser
