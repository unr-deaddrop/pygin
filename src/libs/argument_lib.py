"""
The generic DeadDrop argument handling system, used to define a common interface
across the entire framework that's implementation agnostic.

May also be used for less dynamic fields, such as configuration.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
import abc

from pydantic import BaseModel


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
        """
        Default boolean parsing.

        Includes certain hard-coded value conversions for strings.
        """
        # Hardcoded string-cast values.
        DEFAULT_VALUES = {"True": True, "False": False, "true": True, "false": False}
        if value in DEFAULT_VALUES:
            return DEFAULT_VALUES[value]

        return bool(value)

    @staticmethod
    def parse_string(value) -> str:
        """
        Default string parsing.
        """
        return str(value)

    @staticmethod
    def parse_integer(value) -> int:
        """
        Default integer parsing.
        """
        return int(value)

    @staticmethod
    def parse_float(value) -> float:
        """
        Default float parsing.
        """
        return float(value)

    @staticmethod
    def parse_path(value) -> Path:
        """
        Default path parsing.

        Note that the path is not resolved to avoid making assumptions
        about the path referring to a specific location on this filesystem.
        """
        return Path(value)

    @staticmethod
    def parse_iterable(value: str) -> list[str]:
        """
        Default iterable parsing.

        This simply assumes that a comma-separated list of strings has been
        provided. The result of each string is stripped of whitespace to
        account for lists separated by commas and spaces.
        """
        return [x.strip() for x in value.split(",")]


class Argument(BaseModel):
    """
    Represents a single argument for an arbitrary command.

    Note that it is up to the ArgumentParser instance of a particular CommandBase
    to actually validate commands. No basic type checking is provided.

    Although many of the fields in Argument are *really* immutable elements,
    this is implemented as a Pydantic model for a variety of convenience reasons.
    """

    # The value type this argument is expected to hold.
    arg_type: ArgumentType
    # The name of this argument, used both internally and displayed to the user.
    name: str
    # The long description of this argument. May be valid Markdown.
    description: str
    # Whether or not this argument is required.
    required: bool = True
    # Whether or not this argument is repeatable. `value` may store a single
    # value, such as a string, that is converted to an iterable through
    # `parse_arg()` at runtime.
    is_iterable: bool = False

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

        self._value = self._parser(new_value)


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

    arguments: list[Argument] = []

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Generate a mapping of available argument names to their underlying
        # argument instances.
        self._argument_mapping: dict[str, Argument] = {}

        for arg in self.arguments:
            self._argument_mapping[arg.name] = arg

    def parse_arguments(self, args: dict[str, Any]) -> bool:
        """
        For each argument provided, sets their value.

        Returns True if all required arguments have been set.
        """
        for arg_name, arg_value in args.items():
            if arg_name not in self._argument_mapping:
                raise RuntimeError(f"Unexpected argument {arg_name}")

            try:
                self._argument_mapping[arg_name].value = arg_value
            except Exception as e:
                raise RuntimeError(f"Invalid argument value {arg_value}") from e

        for arg in self.arguments:
            if arg.required and arg.value is None:
                return False

        return True

    def get_stored_args(self) -> dict[str, Any]:
        """
        Convert all arguments to a dictionary.
        """
        result: dict[str, Any] = {}
        for arg in self.arguments:
            result[arg.name] = arg.value

        return result
