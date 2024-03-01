"""
Generic definition of a command, possibly including a reference to a renderer.

TODO: In reality, this should be a completely separate library in a completely
separate repo. But we'll export it later as needed. Again, it's not strictly
needed that this library exists serverside, since everything should just be
passed over to the server as a JSON by an agent, Python or otherwise...
but then you'd need to implement something similar to the below anyways.

This library must not import any other internal libraries; it may only import
the standard library and external packages.
"""

import abc
import json
from enum import Enum
from textwrap import dedent
from typing import Any, ClassVar, Optional, Type

from pydantic import BaseModel

from src.libs.argument_lib import ArgumentParser


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
    data or file listings; currently, renderers provide (un)styled HTML directly.
    In the future, this may instead be consistent with Mythic's approach instead.
    """

    # The specific "format" of the return data.
    renderer_type: ClassVar[RendererType]

    @abc.abstractmethod
    def render_response(self, data: bytes) -> str:
        """
        Render a response as valid HTML.

        In the future, this may change to simply being a JSON document, which
        does not require a change to this specific interface; it would be up to
        the web interface to deal with the change in presentation.

        FIXME: Additionally, note that calling this implies that the interface
        is capable of calling Python code. In the future, it would be necessary
        to make "calling" a command renderer independent of implementation somehow,
        like exposing an actual binary.
        """
        pass


class CommandBase(abc.ABC):
    """
    Class representing the basic definition of a DeadDrop command.

    DeadDrop commands contain the following information:
    - The command name itself, as it should be invoked through the API.
    - A description of the command.
    - The version number of the command.
    - A list of concrete ArgumentBase instances, which dictate the arguments
      that need to be passed into this command.
    - A standard interface through which the command can be called, returning
      a response.

    Additionally, a command *may* provide a repsonse renderer, which
    allows the results of the command to be rendered graphically (or in
    some other format not restricted to plaintext.)

    Note that this leverages Pydantic's built-in serialization for converting
    command definitions into JSON. The process for serialization for complex
    types (such as command parsers and argument renderers) is left up to their
    corresponding instances.
    """

    # The comment below was added when CommandBase was originally intended
    # to be a BaseModel to expose Pydantic's functionality. However, the features
    # aren't *really* needed (and don't work as simply as I'd like for classvars),
    # so I've opted to use Mythic's approach of declaring everything as abstract
    # properties.
    #
    # The same approach isn't used for Argument because it makes a little more
    # sense to leverage stuff like dump_model() and dump_model_json() there.
    # ---
    # The use of abstract properties, as used by Mythic in stock classes,
    # is also valid for Pydantic. See the following link:
    # https://github.com/pydantic/pydantic/discussions/2410
    #
    # In short, the concrete implementation of this class must annotate the
    # associated variables with ClassVar.
    #
    # As expected, decorating with @abc.abstractmethod effectively makes the
    # attribute required; simply decorating with @property does not.

    # command_renderer: ClassVar[Optional[RendererBase]] = None

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def version(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def argument_parser(self) -> Type[ArgumentParser]:
        pass

    @property
    @abc.abstractmethod
    def command_renderer(self) -> Optional[Type[RendererBase]]:
        pass

    @classmethod
    @abc.abstractmethod
    def execute_command(cls, args: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the command.

        In general, commands accept a dictionary of arguments and (eventually)
        generate a payload dictionary as output. It is generally expected that
        the `payload` field is the immediate output of a command completing.

        In general, `execute_command` should assume that the arguments have already
        been parsed by the associated `argument_parser`. This is to decouple
        the execution of a command from the rest of the libraries, as it's not
        necessarily the case that arguments are going to be thrown in as a giant
        dictionary of strings.

        The structure of the `payload` field for command_response messages is
        arbitrary.

        :param args: A dictionary of strings to values.
        """
        pass

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this object to a dictionary suitable for export.

        Note that this also converts the associated commands as exposed by
        the ArgumentParser. The structure is as follows:

        ```json
        {
            "name": str,
            "description": str,
            "version": str,
            "has_renderer": bool,
            "arguments": [
                {
                    // see Argument for exported fields
                }, ...
            ]
        }
        ```

        Note that for compatibility purposes, ensure that the resulting dictionary
        is completely JSON serializable. By extension, this means that Argument
        must have JSON serializable fields, as dictated by `model_dump()`.
        """
        return {
            "name": self.name,
            # `dedent()` removes any leading indentation from the docstring.
            "description": dedent(self.description).strip(),
            "version": self.version,
            "has_renderer": bool(
                self.command_renderer
            ),  # True if one has been assigned.
            "arguments": self.argument_parser().model_dump()["arguments"],
        }

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), **kwargs)


def export_all_commands() -> list[Type[CommandBase]]:
    """
    Return a list of visible command classes.

    The command lookup occurs by inspecting all available subclasses of CommandBase
    when this function is executed.

    Note that "visible" means that the associated subclasses of CommandBase must
    already have been imported. If you implement a script to generate the command JSONs,
    you will need to import the commands ahead of time.
    """
    return CommandBase.__subclasses__()


def get_commands_as_dict() -> dict[str, Type[CommandBase]]:
    """
    Return a dictionary of commands, suitable for lookup.

    The keys are the `name` attribute of each command found; the values are the
    literal types for each command (a subclass of CommandBase).
    """
    # mypy doesn't handle properties well; this works in practice, and the type
    # of cmd.name is *always* str
    return {cmd.name: cmd for cmd in export_all_commands()}  # type: ignore[misc]


def export_commands_as_json(command_classes: list[Type[CommandBase]], **kwargs):
    """
    Return a nicely formatted dictionary containing all command information,
    suitable for presentation in the DeadDrop interface. This is a list of
    JSON objects containing all available commands.

    In the case of this library, we can generally get away with just calling
    the Pydantic JSON validator for the arguments.
    """
    json_objs: list[dict[str, Any]] = []
    for command_class in command_classes:
        json_objs.append(command_class().to_dict())

    return json.dumps(json_objs, **kwargs)
