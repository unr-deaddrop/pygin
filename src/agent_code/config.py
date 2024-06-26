"""
Agent configuration definition and routines.

This module defines a global configuration object that generated at agent
startup and remains constant throughout the lifetime of the agent.
"""

from base64 import b64decode, b64encode
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union
import configparser
import logging
import uuid

from pydantic import BaseModel, field_validator, Field, field_serializer
from pydantic.json_schema import SkipJsonSchema

# json5 is not typed, but we know that json5.load() exists so we're fine
import json5  # type: ignore[import-untyped]

# Intentional star import, with the goal of getting all of the protocol
# configuration objects available.
from src.protocols import *  # noqa: F403, F401
from deaddrop_meta.protocol_lib import ProtocolConfig, export_all_protocol_configs
from deaddrop_meta.interface_lib import MessagingObject

logger = logging.getLogger(__name__)


class PyginSupportedProtocols(str, Enum):
    """
    Enum used to restrict the user (on the JSON schema) to the supported
    protocols.
    """

    dddb_craigslist = "dddb_craigslist"
    dddb_peertube = "dddb_peertube"
    plaintext_tcp = "plaintext_tcp"


class PyginConfig(BaseModel):
    """
    Agent-wide configuration definitions. Includes both non-sensitive and
    sensitive configurations set at runtime.
    """

    # Note that some defaults are declared at the JSON schema level rather than
    # the field level. This is intentional; the defaults are intended to be used
    # to prepopulate form fields, rather than actually making these fields optional.

    # Strictly speaking, these aren't constants and therefore shouldn't be in
    # all caps, but that's the intent.

    # The agent's ID. The server should set this, not the agent; this guarantees
    # uniqueness even in the astronomically low chance a UUIDv4 collides. The
    # preprocessor action indicates to the preprocessor that this should be filled
    # in with a randomly-generated UUID as the default in the schema before
    # presenting the resulting form to the user.
    AGENT_ID: uuid.UUID = Field(
        json_schema_extra={
            "description": "The agent's UUID.",
            "_preprocess_create_id": True,
        },
    )
    DROP_MISDIRECTED_MESSAGES: bool = Field(
        default=True,
        json_schema_extra={
            "description": "Whether to drop messages with a destination ID not for this agent."
        },
    )

    CONTROL_UNIT_THROTTLE_TIME: float = Field(
        default=2,
        json_schema_extra={
            "description": "The time, in seconds, the control unit should sleep on each cycle."
        },
    )

    # These used to not be included in the JSON schema. However, this means they
    # get excluded from the JSON that the frontend generates. That means that
    # instead of these fields being set to null/None, they're just absent altogether.
    #
    # So instead, we're just going to make these readonly, but we'll include them
    # with the schema.
    AGENT_PRIVATE_KEY: SkipJsonSchema[Optional[bytes]] = Field(
        default=None,
        json_schema_extra={
            "description": "The agent's private key as base64.",
            "readOnly": True,  # This doesn't actually affect the form, it's semantic only
        },
    )
    AGENT_PUBLIC_KEY: SkipJsonSchema[Optional[bytes]] = Field(
        default=None,
        json_schema_extra={
            "description": "The agent's public key as base64.",
            "readOnly": True,  # This doesn't actually affect the form, it's semantic only
        },
    )
    ENCRYPTION_KEY: SkipJsonSchema[Optional[bytes]] = Field(
        default=None,
        json_schema_extra={
            "description": "The agent's symmetric encryption key as base64.",
            "readOnly": True,  # This doesn't actually affect the form, it's semantic only
        },
    )

    SERVER_PRIVATE_KEY: SkipJsonSchema[Optional[bytes]] = Field(
        default=None,
        json_schema_extra={
            "description": "The server's private key as base64. Set at runtime.",
            "readOnly": True,  # This doesn't actually affect the form, it's semantic only
        },
    )
    # This *is* visible to the schema. The server is hinted that it should substitute
    # the default value of this with the its own public key, as defined in the app's
    # settings.py (as base64). This should be done in all cases (since the server's
    # public key should never change).
    SERVER_PUBLIC_KEY: Optional[bytes] = Field(
        default=None,
        json_schema_extra={
            "description": "The server's public key as base64.",
            # Let default = settings.SERVER_PUBLIC_KEY
            "_preprocess_settings_val": "SERVER_PUBLIC_KEY",
        },
    )
    # Note that if a message is being received and must be verified, it is up to
    # the server to send its private key independently as part of the "overhead",
    # which includes things like the agent's name, hostname, and other server-levle
    # fields.

    INCOMING_PROTOCOL: PyginSupportedProtocols = Field(
        json_schema_extra={
            "default": PyginSupportedProtocols.plaintext_tcp,
            "description": "The protocol used to receive messages.",
        }
    )

    HEARTBEAT_PROTOCOL: PyginSupportedProtocols = Field(
        json_schema_extra={
            "default": PyginSupportedProtocols.plaintext_tcp,
            "description": "The protocol used to send heartbeats.",
        }
    )
    LOGGING_PROTOCOL: PyginSupportedProtocols = Field(
        json_schema_extra={
            "default": PyginSupportedProtocols.plaintext_tcp,
            "description": "The protocol used to send logs.",
        }
    )
    SENDING_PROTOCOL: PyginSupportedProtocols = Field(
        json_schema_extra={
            "default": PyginSupportedProtocols.plaintext_tcp,
            "description": "The protocol used to send all other messages.",
        }
    )

    LOGGING_INTERVAL: int = Field(
        json_schema_extra={
            "default": 60,
            "description": "The frequency, in seconds, with which log bundles should be conditionally sent.",
        }
    )
    HEARTBEAT_INTERVAL: int = Field(
        json_schema_extra={
            "default": 60,
            "description": "The frequency, in seconds, with which heartbeats should be conditionally sent.",
        }
    )

    REDIS_MESSAGES_SEEN_KEY: str = Field(
        default="_agent_meta-seen-msgs",
        json_schema_extra={
            "description": "The key used by the message dispatch unit to drop duplicate messages."
        },
    )
    REDIS_NEW_MESSAGES_KEY: str = Field(
        default="_agent_meta-new-msg-task-ids",
        json_schema_extra={
            "description": "The key used by the control unit to discover completed message tasking."
        },
    )
    REDIS_MAIN_PROCESS_MESSAGES_SEEN_KEY: str = Field(
        default="_agent_meta-main-msgs-seen",
        json_schema_extra={
            "description": "The key used by the control unit to drop duplicated messages."
        },
    )
    RESULT_RETRIEVAL_REATTEMPT_LIMIT: int = Field(
        default=5,
        json_schema_extra={
            "description": "The number of times a Celery task may be observed to be pending before dropped."
        },
    )

    INCOMING_ENCODED_MESSAGE_DIR: Path = Field(
        default=Path("msgs/incoming_raw"),
        json_schema_extra={
            "description": "The directory used to store incoming messages before decoding."
        },
    )
    INCOMING_DECODED_MESSAGE_DIR: Path = Field(
        default=Path("msgs/incoming_decoded"),
        json_schema_extra={
            "default": "msgs/incoming_decoded",
            "description": "The directory used to store incoming messages after decoding.",
        },
    )
    OUTGOING_DECODED_MESSAGE_DIR: Path = Field(
        default=Path("msgs/outgoing_decoded"),
        json_schema_extra={
            "default": "msgs/outgoing_decoded",
            "description": "The directory used to store outgoing messages before encoding.",
        },
    )
    OUTGOING_ENCODED_MESSAGE_DIR: Path = Field(
        default=Path("msgs/outgoing_raw"),
        json_schema_extra={
            "default": "msgs/outgoing_raw",
            "description": "The directory used to store outgoing messages after encoding.",
        },
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

            proto_cfg_obj = protocol_cfg_type.model_validate(protocol_config)
            cfg_obj.protocol_configuration[protocol_name] = proto_cfg_obj  # type: ignore[index]

        return cfg_obj

    @classmethod
    def from_msg_obj(cls, msg_cfg: MessagingObject) -> "PyginConfig":
        cfg_obj = PyginConfig.model_validate(msg_cfg.agent_config)
        cfg_obj.create_dirs()

        for protocol_cfg_type in export_all_protocol_configs():
            protocol_name = protocol_cfg_type.section_name
            protocol_config = msg_cfg.protocol_config[protocol_name]  # type: ignore[index]

            proto_cfg_obj = protocol_cfg_type.model_validate(protocol_config)
            cfg_obj.protocol_configuration[protocol_name] = proto_cfg_obj  # type: ignore[index]

        return cfg_obj

    @field_validator(
        "AGENT_PRIVATE_KEY",
        "AGENT_PUBLIC_KEY",
        "SERVER_PUBLIC_KEY",
        "SERVER_PRIVATE_KEY",
        mode="before",
    )
    @classmethod
    def validate_base64(cls, v: Any) -> Union[bytes, None]:
        """
        If the value passed into the configuration object is not bytes,
        assume base64.

        If this is an empty string, interpret it as None. This is relevant
        when taking outputs directly from the frontend's form.
        """
        if v is None or isinstance(v, bytes):
            return v

        if v == "":
            return None

        try:
            val = b64decode(v)
        except Exception as e:
            raise ValueError(f"Assumed b64decode of {v} failed.") from e

        return val

    @field_validator("ENCRYPTION_KEY", mode="before")
    @classmethod
    def validate_encryption_key(cls, v: Any) -> Union[bytes, None]:
        """
        If the encryption key passed into the configuration object is not bytes,
        assume base64.

        Then, check that the encryption key is 16, 24, or 32 bytes in length
        (AES-128, AES-192, and AES-256 respectively).
        """
        if v is None or isinstance(v, bytes):
            return v

        if v == "":
            return None

        try:
            val = b64decode(v)
        except Exception as e:
            raise ValueError(f"Assumed b64decode of {v} failed.") from e

        if len(val) not in (16, 24, 32):
            raise ValueError("Decoded key is of invalid length.")

        return val

    # @field_validator("INCOMING_PROTOCOLS", mode="before")
    # @classmethod
    # def validate_incoming_protocols(cls, v: Any) -> list[str]:
    #     """
    #     If the incoming protocol set is not a list, assume that it is a
    #     comma-separated string.
    #     """
    #     if isinstance(v, list):
    #         return v

    #     if not isinstance(v, str):
    #         raise ValueError(f"Expected string or list, got {v}")

    #     return [x.strip() for x in v.split(",")]

    @field_serializer(
        "AGENT_PRIVATE_KEY",
        "AGENT_PUBLIC_KEY",
        "SERVER_PUBLIC_KEY",
        "SERVER_PRIVATE_KEY",
        "ENCRYPTION_KEY",
        when_used="json-unless-none",
    )
    @classmethod
    def serialize_bytes(cls, v: bytes) -> str:
        """
        Turn bytes into their base64 representation before it pops out of a JSON file.
        """
        return b64encode(v).decode("utf-8")

    @field_serializer("protocol_configuration")
    @classmethod
    def serialize_protocol_cfg(cls, cfg: dict[str, ProtocolConfig]) -> dict[str, Any]:
        """
        Convert the dictionary of ProtocolConfig elements recursively.

        Pydantic (for some reason) doesn't seem to do this, so we convert the field
        ourselves.
        """
        return {k: v.model_dump() for k, v in cfg.items()}

    def as_standard_json(self) -> str:
        """
        Convert the model to the standard build JSON format.

        In short, the model is converted to the following:
        ```json
        {
            "agent_config":{
                ...
            },
            "protocol_config":{
                ...
            }
        }
        ```
        """
        # Dump the entire model as-is to JSON; Pydantic can handle the conversion
        # of unusual types like UUID, but json/json5 cannot.
        model_json = self.model_dump_json()

        # Read the whole thing back in.
        data = json5.loads(model_json)

        # Pop the protocol configuration key, have that be its own dictionary
        proto_cfg = data.pop("protocol_configuration")

        # Construct the final result. Various formatting options are applied to
        # make it as close to stock JSON as possible.
        return json5.dumps(
            {"agent_config": data, "protocol_config": proto_cfg},
            quote_keys=True,
            trailing_commas=False,
            indent=2,
        )

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
            getattr(self, field).resolve().mkdir(exist_ok=True, parents=True)  #
