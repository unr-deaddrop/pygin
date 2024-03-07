"""
Agent configuration definition and routines.

This module defines a global configuration object that generated at agent
startup and remains constant throughout the lifetime of the agent.
"""

from base64 import b64decode
from pathlib import Path
from typing import Any, Optional
import configparser
import uuid

from pydantic import BaseModel, field_validator, Field
from pydantic.json_schema import SkipJsonSchema

# json5 is not typed, but we know that json5.load() exists so we're fine
import json5  # type: ignore[import-untyped]

# Intentional star import, with the goal of getting all of the protocol
# configuration objects available.
from src.protocols import *  # noqa: F403, F401
from deaddrop_meta.protocol_lib import ProtocolConfig, export_all_protocol_configs


class PyginConfig(BaseModel):
    """
    Agent-wide configuration definitions. Includes both non-sensitive and
    sensitive configurations set at runtime.

    See agent.cfg for more details.
    """

    # Strictly speaking, these aren't constants and therefore shouldn't be in
    # all caps, but that's the intent.
    AGENT_ID: uuid.UUID = Field(json_schema_extra={"description": "The agent's UUID."})

    CONTROL_UNIT_THROTTLE_TIME: float = Field(
        default=2,
        json_schema_extra={
            "description": "The time, in seconds, the control unit should sleep on each cycle."
        },
    )

    # These are generated at build time and are not user configured, and therefore
    # should not be included in any forms constructed from this schema. In turn,
    # the payload generation script is responsible for actually creating these with
    # the configuration file.
    #
    # That said, the json_schema_extra fields are filled out anyways since I didn't
    # want to lose them if we had to turn around.
    AGENT_PRIVATE_KEY_PATH: SkipJsonSchema[Optional[Path]] = Field(
        json_schema_extra={"description": "The path to the agent's private key."}
    )
    SERVER_PUBLIC_KEY_PATH: SkipJsonSchema[Optional[Path]] = Field(
        json_schema_extra={"description": "The path to the agent's public key."}
    )
    ENCRYPTION_KEY: SkipJsonSchema[bytes] = Field(
        json_schema_extra={
            "description": "The agent's symmetric encryption key, base64 encoded."
        }
    )

    INCOMING_PROTOCOLS: list[str] = Field(
        json_schema_extra={
            "description": "A list of supported agent names for which periodic listener tasks should be scheduled."
        }
    )

    HEARTBEAT_PROTOCOL: str = Field(
        json_schema_extra={"description": "The protocol used to send heartbeats."}
    )
    LOGGING_PROTOCOL: str = Field(
        json_schema_extra={"description": "The protocol used to send log bundles."}
    )
    SENDING_PROTOCOL: str = Field(
        json_schema_extra={
            "description": "The protocol used to send all other messages."
        }
    )

    LOGGING_INTERVAL: int = Field(
        json_schema_extra={
            "description": "The frequency, in seconds, with which log bundles should be conditionally sent."
        }
    )
    HEARTBEAT_INTERVAL: int = Field(
        json_schema_extra={
            "description": "The frequency, in seconds, with which heartbeats should be conditionally sent."
        }
    )

    REDIS_MESSAGES_SEEN_KEY: str = Field(
        json_schema_extra={
            "description": "The key used by the message dispatch unit to drop duplicate messages."
        }
    )
    REDIS_NEW_MESSAGES_KEY: str = Field(
        json_schema_extra={
            "description": "The key used by the control unit to discover completed message tasking."
        }
    )
    REDIS_MAIN_PROCESS_MESSAGES_SEEN_KEY: str = Field(
        json_schema_extra={
            "description": "The key used by the control unit to drop duplicated messages."
        }
    )
    RESULT_RETRIEVAL_REATTEMPT_LIMIT: int = Field(
        json_schema_extra={
            "description": "The number of times a Celery task may be observed to be pending before dropped."
        }
    )

    INCOMING_ENCODED_MESSAGE_DIR: Path = Field(
        json_schema_extra={
            "description": "The directory used to store incoming messages before decoding."
        }
    )
    INCOMING_DECODED_MESSAGE_DIR: Path = Field(
        json_schema_extra={
            "description": "The directory used to store incoming messages after decoding."
        }
    )
    OUTGOING_DECODED_MESSAGE_DIR: Path = Field(
        json_schema_extra={
            "description": "The directory used to store outgoing messages before encoding."
        }
    )
    OUTGOING_ENCODED_MESSAGE_DIR: Path = Field(
        json_schema_extra={
            "description": "The directory used to store outgoing messages after encoding."
        }
    )

    # Configuration objects for each protocol. This is excluded from the JSON
    # schema generation, since it's handled completely separately. The JSON schema
    # only covers general agent configuration; the JSON file passed for build
    # configuration is composed of global configuration, and *then* protocol-specific
    # configuration.
    #
    # The reason for this is that it's not necessarily the case a user wants to
    # configure *every* supported protocol for an agent. So the protocol configuration
    # is handled as part of the payload generation script completely separately
    # from the main config schema.
    protocol_configuration: SkipJsonSchema[dict[str, ProtocolConfig]] = {}

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

    @classmethod
    def from_json5_file(cls, cfg_path: Path) -> "PyginConfig":
        """
        Construct the global Pygin configuration object from a JSON5-compliant
        file.

        This assumes that Pygin's configuration is under the top-level key
        "agent_config", while each protocol's configuration is a separate
        key under the top-level key "protocol_config".
        """
        # Read the full file
        with open(cfg_path) as fp:
            data = json5.load(fp)

        # Retrieve agent configuration, instantiate the model without
        # protocol configuration
        cfg_obj = PyginConfig.model_validate(data["agent_config"])
        cfg_obj.create_dirs()

        # Now, for each built-in protocol, generate their configuration and add
        # it to our own.
        #
        # The type ignore is, again, due to properties.
        for protocol_cfg_type in export_all_protocol_configs():
            protocol_name = protocol_cfg_type.section_name
            protocol_config = data["protocol_config"][protocol_name]
            cfg_obj.protocol_configuration[protocol_name] = (  # type: ignore[index]
                protocol_cfg_type.model_validate(protocol_config)
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
