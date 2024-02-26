"""
dddb-specific routines for operating "locally".

This assumes that the server (or some other source of messages) has access
to the local folders that the agent reads message from and writes messaages to.
This is useful in single-device demonstrations of DeadDrop, as well as remote
demonstrations of DeadDrop that do not involve an actual remote service.
"""

from pathlib import Path
from typing import Type, Any, ClassVar


from src.libs.argument_lib import Argument, ArgumentType, DefaultParsers
from src.libs.protocol_lib import (
    ProtocolBase,
    ProtocolConfig,
    ProtocolArgumentParser,
    DeadDropMessage,
)


class dddbLocalConfig(ProtocolConfig):
    """
    Model detailing available configuration options for dddb_local.
    """

    DDDB_LOCAL_CHECKIN_FREQUENCY: int
    DDDB_LOCAL_INBOX_DIR: Path
    DDDB_LOCAL_OUTBOX_DIR: Path

    # Should be dddb_local
    _: ClassVar[str] = "dddb_local"
    _dir_attrs: ClassVar[list[str]] = ["DDDB_LOCAL_INBOX_DIR", "DDDB_LOCAL_OUTBOX_DIR"]


class dddbLocalArgumentParser(ProtocolArgumentParser):
    """
    Parser for the dddb_local configuration.
    """

    arguments: list[Argument] = [
        Argument(
            arg_type=ArgumentType.INTEGER,
            name="DDDB_LOCAL_CHECKIN_FREQUENCY",
            description="The frequency with which to check for new messages.",
            _parser=DefaultParsers.parse_integer,
        ),
        Argument(
            arg_type=ArgumentType.PATH,
            name="DDDB_LOCAL_INBOX_DIR",
            description="The location to expect incoming messages in.",
            _parser=DefaultParsers.parse_path,
        ),
        Argument(
            arg_type=ArgumentType.PATH,
            name="DDDB_LOCAL_INBOX_DIR",
            description="The location to send outgoing messages to.",
            _parser=DefaultParsers.parse_path,
        ),
    ]


class dddbLocalProtocol(ProtocolBase):
    """
    Local implementation of the dddb protocol.

    This leverages the local filesystem to "send" and "receive" videos, such that
    the server and the agent have agreed on folders for incoming and outgoing
    messages in advance.

    While this does not use an external protocol as intended by the framework,
    this demonstrates a proof-of-concept that avoids depending on an external
    service outside of our control.
    """

    name: str = "dddb_local"
    description: str = __doc__
    version: str = "0.0.1"
    config_parser: Type[ProtocolArgumentParser] = dddbLocalArgumentParser

    @classmethod
    def send_msg(cls, msg: DeadDropMessage, args: dict[str, Any]) -> bytes:
        raise NotImplementedError

    @classmethod
    def get_new_messages(cls, args: dict[str, Any]) -> list[DeadDropMessage]:
        raise NotImplementedError
