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

# This was originally used for importing configuration files as a dictionary,
# but we've opted to generalize it to ConfigParser for now
# from dotenv import dotenv_values
from pydantic import BaseModel, field_validator


class PyginConfig(BaseModel):
    """
    Agent-wide configuration definitions. Includes both non-sensitive and
    sensitive configurations set at runtime.

    See agent.cfg for more details.
    """

    # Strictly speaking, these aren't constants and therefore shouldn't be in
    # all caps, but that's the intent.
    AGENT_ID: uuid.UUID

    AGENT_PRIVATE_KEY_PATH: Path
    SERVER_PUBLIC_KEY_PATH: Path

    ENCRPYTION_KEY: bytes

    INCOMING_ENCODED_MESSAGE_DIR: Path
    INCOMING_DECODED_MESSAGE_DIR: Path
    OUTGOING_DECODED_MESSAGE_DIR: Path
    OUTGOING_ENCODED_MESSAGE_DIR: Path

    # The names of all object attributes that are directories and should be
    # resolved and created upon creation. Attributes with leading underscores
    # are excluded from Pydantic model validation.
    _DIR_ATTRS = (
        "INCOMING_ENCODED_MESSAGE_DIR",
        "INCOMING_DECODED_MESSAGE_DIR",
        "OUTGOING_DECODED_MESSAGE_DIR",
        "OUTGOING_ENCODED_MESSAGE_DIR",
    )

    @classmethod
    def from_cfg_file(cls, cfg_path: Path) -> "PyginConfig":
        """
        Construct the global Pygin configuration object from a file.
        
        Note that this also recursively creates the directories specified in the
        configuration file.
        """
        cfg_parser = configparser.ConfigParser()
        cfg_parser.read(cfg_path)
        cfg_obj = PyginConfig.model_validate(cfg_parser["pygin"])
        cfg_obj.create_dirs()
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
