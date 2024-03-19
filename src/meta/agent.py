"""
Static metadata definitions for Pygin.
"""

from typing import Type

from pydantic import BaseModel

from deaddrop_meta.agent_lib import SupportedOSTypes, SupportedProtocols, AgentBase

from src.agent_code.config import PyginConfig


class PyginInfo(AgentBase):
    """
    Pygin is the reference implementation of a DeadDrop agent.

    Although written in Python and therefore generally platform-agnostic,
    this depends on Redis as its Celery broker and database. In general,
    this is only available on Linux.
    """

    name: str = "pygin"
    description: str = __doc__
    version: str = "0.2.2"
    author: str = "lgactna"
    source: str = "https://github.com/unr-deaddrop/pygin/"
    supported_operating_systems: list[SupportedOSTypes] = [SupportedOSTypes.LINUX]
    supported_protocols: list[SupportedProtocols] = [
        SupportedProtocols.DDDB_LOCAL,
        SupportedProtocols.DDDB_YOUTUBE,
        SupportedProtocols.PLAINTEXT_LOCAL,
    ]
    config_model: Type[BaseModel] = PyginConfig
