"""
Agent configuration definition and routines.

This module defines a global configuration object that generated at agent
startup and remains constant throughout the lifetime of the agent.
"""

from base64 import b64decode
from pathlib import Path
from typing import Any
import configparser
import uuid

from pydantic import BaseModel, field_validator

# Intentional star import, with the goal of getting all of the protocol
# configuration objects available.
from src.protocols import *  # noqa: F403, F401
from src.libs.protocol_lib import ProtocolConfig, export_all_protocol_configs


class PyginConfig(BaseModel):
    """
    Agent-wide configuration definitions. Includes both non-sensitive and
    sensitive configurations set at runtime.

    See agent.cfg for more details.
    """

    # Strictly speaking, these aren't constants and therefore shouldn't be in
    # all caps, but that's the intent.
    AGENT_ID: uuid.UUID

    CONTROL_UNIT_THROTTLE_TIME: float

    AGENT_PRIVATE_KEY_PATH: Path
    SERVER_PUBLIC_KEY_PATH: Path

    ENCRYPTION_KEY: bytes

    INCOMING_PROTOCOLS: list[str]

    HEARTBEAT_PROTOCOL: str
    LOGGING_PROTOCOL: str
    SENDING_PROTOCOL: str

    LOGGING_INTERVAL: int
    HEARTBEAT_INTERVAL: int

    REDIS_MESSAGES_SEEN_KEY: str
    REDIS_NEW_MESSAGES_KEY: str
    REDIS_MAIN_PROCESS_MESSAGES_SEEN_KEY: str
    RESULT_RETRIEVAL_REATTEMPT_LIMIT: int

    INCOMING_ENCODED_MESSAGE_DIR: Path
    INCOMING_DECODED_MESSAGE_DIR: Path
    OUTGOING_DECODED_MESSAGE_DIR: Path
    OUTGOING_ENCODED_MESSAGE_DIR: Path

    # Configuration objects for each protocol.
    protocol_configuration: dict[str, ProtocolConfig] = {}

    # The names of all object attributes that are directories and should be
    # resolved and created upon creation. Attributes with leading underscores
    # are excluded from Pydantic model validation.
    _DIR_ATTRS = [
        "INCOMING_ENCODED_MESSAGE_DIR",
        "INCOMING_DECODED_MESSAGE_DIR",
        "OUTGOING_DECODED_MESSAGE_DIR",
        "OUTGOING_ENCODED_MESSAGE_DIR",
    ]

    @classmethod
    def from_cfg_file(cls, cfg_path: Path) -> "PyginConfig":
        """
        Construct the global Pygin configuration object from a file.

        Note that this also recursively creates the directories specified in the
        configuration file.
        """
        # Use the built-in configparser to get things
        cfg_parser = configparser.ConfigParser()
        cfg_parser.read(cfg_path)

        # Instantiate the Pygin configuration model
        cfg_obj = PyginConfig.model_validate(cfg_parser["pygin"])
        cfg_obj.create_dirs()

        # Now, for each built-in protocol, generate their configuration and add
        # it to our own.
        #
        # The type ignore is, again, due to properties.
        for protocol_cfg_type in export_all_protocol_configs():
            protocol_name = protocol_cfg_type.section_name
            cfg_obj.protocol_configuration[protocol_name] = (  # type: ignore[index]
                protocol_cfg_type.from_cfg_parser(cfg_parser)
            )

        return cfg_obj

    @field_validator("ENCRYPTION_KEY", mode="before")
    @classmethod
    def validate_encryption_key(cls, v: Any) -> bytes:
        """
        If the encryption key passed into the configuration object is not bytes,
        assume base64.

        Then, check that the encryption key is 16, 24, or 32 bytes in length
        (AES-128, AES-192, and AES-256 respectively).
        """
        if type(v) is not bytes:
            try:
                v = b64decode(v)
            except Exception as e:
                raise ValueError(f"Assumed b64decode of {v} failed.") from e

        if len(v) not in (16, 24, 32):
            raise ValueError("Decoded key is of invalid length.")

        return v

    @field_validator("INCOMING_PROTOCOLS", mode="before")
    @classmethod
    def validate_incoming_protocols(cls, v: Any) -> list[str]:
        """
        Split apart the incoming protocols as needed. This is a comma-separated
        string in the configuration file, and therefore may need to be split
        apart manually before Pydantic gets to it.
        """
        if type(v) is str:
            return v.split(",")

        if type(v) is list:
            return v

        raise ValueError("Unexpected type for INCOMING_PROTOCOLS")

    def resolve_all_dirs(self) -> None:
        """
        Resolve and store all relevant config variables.
        """
        for field in self._DIR_ATTRS:
            setattr(self, field, getattr(self, field).resolve())

    def create_dirs(self) -> None:
        """
        Create all associated directories.
        """
        for field in self._DIR_ATTRS:
            getattr(self, field).resolve().mkdir(exist_ok=True, parents=True)
