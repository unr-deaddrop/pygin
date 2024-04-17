"""
Plaintext filesystem implementation of the dddb messaging protocol.

Used for debugging, doesn't have any dependencies.
"""

from pathlib import Path
from typing import Type, Any, ClassVar
from tempfile import NamedTemporaryFile
import logging

from pydantic import Field

from deaddrop_meta.protocol_lib import (
    ProtocolBase,
    ProtocolConfig,
    DeadDropMessage,
)
from deaddrop_meta.interface_lib import EndpointMessagingData

logger = logging.getLogger(__name__)


class PlaintextLocalConfig(ProtocolConfig):
    """
    Model detailing available configuration options for plaintext_local.
    """

    PLAINTEXT_LOCAL_CHECKIN_FREQUENCY: int = Field(
        default=5,
        json_schema_extra={
            "description": "The frequency with which to check for new messages."
        },
    )
    PLAINTEXT_LOCAL_INBOX_DIR: Path = Field(
        default=Path("plaintext_local/inbox"),
        json_schema_extra={
            "description": "The location to expect incoming messages in."
        },
    )
    PLAINTEXT_LOCAL_OUTBOX_DIR: Path = Field(
        default=Path("plaintext_local/outbox"),
        json_schema_extra={"description": "The location to send outgoing messages to."},
    )

    # Should be plaintext_local
    checkin_interval_name: ClassVar[str] = "PLAINTEXT_LOCAL_CHECKIN_FREQUENCY"
    section_name: ClassVar[str] = "plaintext_local"
    dir_attrs: ClassVar[list[str]] = [
        "PLAINTEXT_LOCAL_INBOX_DIR",
        "PLAINTEXT_LOCAL_OUTBOX_DIR",
    ]

    def convert_to_server_config(
        self, endpoint: EndpointMessagingData
    ) -> "PlaintextLocalConfig":
        raise NotImplementedError


class PlaintextLocalProtocol(ProtocolBase):
    """
    Plaintext implementation of the DeadDrop standard messaging system.

    This is similar in function to dddb_local, but entirely operates on plaintext
    JSON documents stored as files. It avoids the dependency hell of dddb and helps
    simplify testing and debugging. The remainder of the description is identical
    to dddb_local.

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

    name: str = "plaintext_local"
    description: str = __doc__
    version: str = "0.0.1"
    config_model: Type[ProtocolConfig] = PlaintextLocalConfig
    supports_bytes: bool = False

    @classmethod
    def send_msg(cls, msg: DeadDropMessage, args: dict[str, Any]) -> dict[str, Any]:
        # dddb_local doesn't leverage anything fancy. For readability, we'll
        # convert our argument dictionary back into the dddb_local config object.
        local_cfg = PlaintextLocalConfig.model_validate(args)

        # Calculate the message's filename.
        filename = f"{msg.message_id}.json"

        # Dump the message as a JSON string in our outbox folder.
        target_path = local_cfg.PLAINTEXT_LOCAL_OUTBOX_DIR / filename

        logger.info(
            f"Writing message ({msg.message_id=}, {msg.payload.message_type=}) to {target_path}"
        )
        logger.debug(f"Writing {msg} to {target_path}")

        with open(target_path, "wt+") as fp:
            fp.write(msg.model_dump_json())

        # Arbitrary return response.
        return {"filepath": target_path, "filename": filename}

    @classmethod
    def get_new_messages(cls, args: dict[str, Any]) -> list[DeadDropMessage]:
        # note that this literally just gets *all* messages, it's the agent's
        # problem to figure out what's actually new
        local_cfg = PlaintextLocalConfig.model_validate(args)

        result: list[DeadDropMessage] = []

        for filepath in local_cfg.PLAINTEXT_LOCAL_INBOX_DIR.glob("*.json"):
            with open(filepath, "rt") as fp:
                msg = DeadDropMessage.model_validate_json(fp.read())
                result.append(msg)

        return result
