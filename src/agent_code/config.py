"""
Agent configuration definition and routines.

This module defines a global configuration object that generated at agent
startup and remains constant throughout the lifetime of the agent.
"""

from pathlib import Path
import uuid

from dotenv import dotenv_values
from pydantic import BaseModel


class Config(BaseModel):
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
    def from_cfg_file(cls, cfg_path: Path) -> "Config":
        # TODO: Probably this shouldn't be dotenv, but Python's builtin
        cfg_obj = Config.model_validate(dotenv_values(cfg_path))
        cfg_obj.create_dirs()
        return cfg_obj

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
