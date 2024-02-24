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
from pathlib import Path
from typing import Any, Callable, ClassVar, Optional, Type

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
        to make "calling" a command renderer independent of implementation.
        """
        pass


class ArgumentType(str, Enum):
    """
    Enumeration of available argument types.
    """

    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    PATH = "filepath"
    ITERABLE = "iterable"


class DefaultParsers:
    """
    Stock argument parsers.
    """

    @staticmethod
    def parse_boolean(value) -> bool:
        # Hardcoded string-cast values.
        DEFAULT_VALUES = {"True": True, "False": False, "true": True, "false": False}
        if value in DEFAULT_VALUES:
            return DEFAULT_VALUES[value]

        return bool(value)

    @staticmethod
    def parse_string(value) -> str:
        return str(value)

    @staticmethod
    def parse_integer(value) -> int:
        return int(value)

    @staticmethod
    def parse_float(value) -> float:
        return float(value)

    @staticmethod
    def parse_path(value) -> Path:
        """
        Returns
        """
        return Path(value)


class Argument(BaseModel):
    """
    Represents a single argument for an arbitrary command.

    Note that it is up to the ArgumentParser instance of a particular CommandBase
    to actually validate commands. No basic type checking is provided.
    """

    # The value type this argument is expected to hold.
    cmd_type: ArgumentType
    # The name of this argument, used both internally and displayed to the user.
    name: str
    # The long description of this argument. May be valid Markdown.
    description: str
    # Whether or not this argument is required.
    required: bool
    # Whether or not this argument is repeatable. `value` may store a single
    # value, such as a string, that is converted to an iterable through
    # `parse_arg()` at runtime.
    is_iterable: bool

    default: Optional[Any] = None

    # The parser function used to convert incoming values into their final datatype,
    # if any. The default behavior is for the value to be used as-is.
    _parser: Optional[Callable[..., Any]] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.value = self.default

    # The value (or default value) currently associated with this argument.
    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, new_value) -> None:
        """
        Setter for the value. Override _parser if you want to change
        the behavior of this field.

        By default, this simply uses `new_value` as-is. However, it may be
        desirable to convert `value` into a different native Python datatype
        before executing the command, such as if a list has been stored as a
        string.
        """
        if not self._parser:
            self._value = new_value
            return

        self._value = self._parser(new_value)  # type: ignore


class ArgumentParser(BaseModel, abc.ABC):
    """
    Class containing logic for parsing the arguments passed into a single
    command.

    For each command that you write that requires arguments, you will need to
    implement this class and set it as the command's `argument_parser`. The
    expectation at runtime is that the implementation of this class is used
    to auto-magically parse the arguments in a manner that is independent of
    the command's implementation.

    Additionally, this guarantees that different instances of Argument are
    used each time a command is called, as an instance of ArgumentParser
    is created each time.
    """

    arguments: ClassVar[list[Argument]]

    def __init__(self, arguments: list[Argument], **kwargs):
        super().__init__(arguments, **kwargs)

        # Generate a mapping of available argument names to their underlying
        # argument instances.
        self._argument_mapping: dict[str, Argument] = {}

        for arg in self.arguments:
            self._argument_mapping[arg.name] = arg

    def parse_arguments(self, args: dict[str, Any]) -> None:
        """
        For each argument provided, sets their value.
        """
        for arg_name, arg_value in args.items():
            if arg_name not in self._argument_mapping:
                raise RuntimeError(f"Unexpected argument {arg_name}")

            try:
                self._argument_mapping[arg_name] = arg_value
            except Exception as e:
                raise RuntimeError(f"Invalid argument value {arg_value}") from e

    def get_stored_args(self) -> dict[str, Any]:
        """
        Convert all arguments to a dictionary.
        """
        result: dict[str, Any] = {}
        for arg in self.arguments:
            result[arg.name] = arg.value

        return result


class CommandBase(BaseModel, abc.ABC):
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

    # The below is no longer relevant, but is still kept for completeness:
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
    # ---

    name: ClassVar[str]
    description: ClassVar[str]
    version: ClassVar[str]
    argument_parser: ClassVar[Type[ArgumentParser]]

    command_renderer: Optional[RendererBase] = None

    @abc.abstractmethod
    def execute_command(self, **kwargs) -> bytes:
        """
        Execute the command.
        """
        pass


def export_all_commands() -> list[Type[CommandBase]]:
    """
    Return a list of visible command classes.
    """
    # TODO: I don't know how reliable this is. On paper, I feel like it should
    # just work if you import `commands` and then call this, but is that correct?
    return CommandBase.__subclasses__()


def export_commands_as_json(command_classes: list[Type[CommandBase]]):
    """
    Return a nicely formatted dictionary containing all command information,
    suitable for presentation in the DeadDrop interface. This is a list of
    JSON objects containing all available commands.

    In the case of this library, we can generally get away with just calling
    the Pydantic JSON validator over and over again.
    """
    json_objs: list[str] = []
    for command_class in command_classes:
        json_objs.append(command_class.model_dump_json())

    result = ",".join(json_objs)
    data = json.loads(f"[{result}]")
    return json.dumps(data, indent=4)
