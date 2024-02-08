"""
Generic definition of a command, possibly including a reference to a renderer.

TODO: In reality, this should be a completely separate library in a completely separate
repo. But we'll export it later as needed.
"""

import abc

from enum import Enum
from pydantic import BaseModel


class RendererType(str, Enum):
    """
    Enumeration of available renderer types.
    """

    TABULAR = "tabular"
    FILE_LISTING = "file_listing"


class RendererBase(BaseModel, abc.ABC):
    """
    Abstract definition of a command response renderer.

    This class provides functionality for interpreting the results of specific
    instances of CommandBase (i.e. specific commands); it should return a valid

    FIXME: Note that Mythic has specific render "types", such as generic tabular
    data or file listings; currently, renders provide (un)styled HTML directly.
    In the future, this may instead be consistent with Mythic's approach instead.
    """

    @property
    @abc.abstractmethod
    def renderer_type(self) -> RendererType:
        """
        The specific "format" of the return data.
        """
        pass

    @abc.abstractmethod
    def render_response(self, data: bytes) -> str:
        """
        Render a response as valid HTML.

        In the future, this may change to simply being a JSON document, which
        does not require a change to this specific interface; it would be up to
        the web interface to deal with the change in presentation.
        """
        pass


class CommandBase(BaseModel, abc.ABC):
    """ """

    # The use of abstract properties, as used by Mythic in stock classes,
    # is also valid for Pydantic - see https://github.com/pydantic/pydantic/discussions/2410
    @property
    @abc.abstractmethod
    def command_name(self) -> str:
        pass


def export_all_commands():
    """
    Return a list of available command classes.
    """
    pass


def export_commands_as_json():
    """
    Return a nicely formatted dictionary containing all command information,
    suitable for presentation in the DeadDrop interface.
    """
    pass
