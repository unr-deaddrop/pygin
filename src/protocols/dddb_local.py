"""
dddb-specific routines for operating "locally".

This assumes that the server (or some other source of messages) has access
to the local folders that the agent reads message from and writes messaages to.
This is useful in single-device demonstrations of DeadDrop, as well as remote
demonstrations of DeadDrop that do not involve an actual remote service.
"""

from pathlib import Path
from typing import Type, Any, ClassVar
from tempfile import NamedTemporaryFile

from pydantic import Field

from deaddrop_meta.protocol_lib import (
    ProtocolBase,
    ProtocolConfig,
    DeadDropMessage,
)


class dddbLocalConfig(ProtocolConfig):
    """
    Model detailing available configuration options for dddb_local.
    """

    DDDB_LOCAL_CHECKIN_FREQUENCY: int = Field(
        json_schema_extra={
            "description": "The frequency with which to check for new messages."
        }
    )
    DDDB_LOCAL_INBOX_DIR: Path = Field(
        json_schema_extra={
            "description": "The location to expect incoming messages in."
        }
    )
    DDDB_LOCAL_OUTBOX_DIR: Path = Field(
        json_schema_extra={"description": "The location to send outgoing messages to."}
    )

    # Should be dddb_local
    checkin_interval_name: ClassVar[str] = "DDDB_LOCAL_CHECKIN_FREQUENCY"
    section_name: ClassVar[str] = "dddb_local"
    dir_attrs: ClassVar[list[str]] = ["DDDB_LOCAL_INBOX_DIR", "DDDB_LOCAL_OUTBOX_DIR"]

    def convert_to_server_config(self) -> "dddbLocalConfig":
        raise NotImplementedError


class dddbLocalProtocol(ProtocolBase):
    """
    Local implementation of the dddb protocol.

    This leverages the local filesystem to "send" and "receive" videos, such that
    the server and the agent have agreed on folders for incoming and outgoing
    messages in advance.

    While this does not use an external protocol as intended by the framework,
    this demonstrates a proof-of-concept that avoids depending on an external
    service outside of our control.

    Note that this protocol is extremely simple with respect to error handling
    and local storage space; it makes no attempt at filtering out messages that
    have already been read, and simply returns all available messages. It is up
    to higher-level code to filter out messages that have already been seen.

    That is to say, this protocol does not keep track of the most recently viewed
    message.
    """

    name: str = "dddb_local"
    description: str = __doc__
    version: str = "0.0.1"
    config_model: Type[ProtocolConfig] = dddbLocalConfig

    @classmethod
    def send_msg(cls, msg: DeadDropMessage, args: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

        # dddb_local doesn't leverage anything fancy. For readability, we'll
        # convert our argument dictionary back into the dddb_local config object.
        local_cfg = dddbLocalConfig.model_validate(args)

        # Dump the message as a JSON string, storing it in a temporary file.
        with NamedTemporaryFile("w+t") as fp:
            fp.write(msg.model_dump_json())

            # TODO: Have this actually use dddb. For now, we're basically just using
            # plaintext to simulate having dddb; in reality, dddb would accept a filepath
            # here.
            temp_path = Path(fp.name).resolve()

    @classmethod
    def get_new_messages(cls, args: dict[str, Any]) -> list[DeadDropMessage]:
        # print some log messages about how it's checking so-and-so folder
        raise NotImplementedError
