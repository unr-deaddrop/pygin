"""
Library adhering to the standard definition of a DeadDrop agent.

Although this can be used at runtime, its intended purpose is to facilitate
exposing various metadata to the server. This defines certain constants
that are intended to be shared across all agents (including those not
written in Python), such that a JSON metadata file can be generated
for the agent.
"""

from enum import Enum
from textwrap import dedent
from typing import Any, Type
import abc
import json

from pydantic import BaseModel

from src.libs.argument_lib import ArgumentParser


class SupportedOSTypes(str, Enum):
    """
    Enumeration of available operating systems supported by the entire framework.
    """

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "mac"


class SupportedProtocols(str, Enum):
    """
    Enumeration of supported protocols.

    Naturally, this enumeration will never be "complete" if others without access
    to this library write new protocols. In turn, the names of protocols would
    simply have to be agreed upon in future agents and protocols.

    However, for the sake of this project, we'll list all "reference" protocols
    here.
    """

    DDDB_LOCAL = "dddb_local"
    DDDB_YOUTUBE = "dddb_youtube"
    PLAINTEXT_LOCAL = "plaintext_local"


class AgentBase(abc.ABC):
    """
    The generic agent definition class. This specifies the static metadata
    fields that agents are expected to define.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        The global name used for this agent.
        """
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """
        A brief description of this agent.

        The "source" should redirect the user to documentation if needed.
        """
        pass

    @property
    @abc.abstractmethod
    def version(self) -> str:
        """
        The version string for this agent.
        """
        pass

    @property
    @abc.abstractmethod
    def author(self) -> str:
        """
        The agent's author(s).
        """
        pass

    @property
    @abc.abstractmethod
    def source(self) -> str:
        """
        A link to the agent's source code.
        """
        pass

    @property
    @abc.abstractmethod
    def supported_operating_systems(self) -> list[SupportedOSTypes]:
        """
        A list of named and recognized operating systems this agent supports.
        """
        pass

    @property
    @abc.abstractmethod
    def supported_protocols(self) -> list[SupportedProtocols]:
        """
        A list of named and recognized protocols this agent supports.
        """
        pass

    @property
    @abc.abstractmethod
    def config_parser(self) -> Type[ArgumentParser]:
        """
        The configuration/argument parser for this agent.

        See protocol_lib.py for details on why we use ArgumentParser,
        originally built for commands, as a way to expose the available
        configuration options for this agent.
        """
        pass

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this agent to a dictionary suitable for export.

        The structure is as follows:
        ```json
        {
            "name": str,
            "description": str,
            "version": str,
            "author": str,
            "source": str,
            "operating_systems": list[str],
            "protocols": list[str],
            "config": [
                {
                    // See Argument for what this looks like
                }
            ]
        }
        ```

        As always, ensure that the resulting dictionary is JSON serializable.
        """
        return {
            "name": self.name,
            "description": dedent(self.description).strip(),
            "version": self.version,
            "author": self.author,
            "source": self.source,
            "operating_systems": self.supported_operating_systems,
            "protocols": self.supported_protocols,
            "config": self.config_parser().model_dump()["arguments"],
        }

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), **kwargs)
