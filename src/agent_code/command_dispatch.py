"""
This implements the command dispatch module as described in DeadDrop's
generic architecture model for agents.

If any additional operations are needed before handing the message off to
a particular command, it should be done here. This may include adding
command-specific arguments that are not already present in the configuration
object, and therefore must be handled on a case-by-case basis.

The spirit of this design is that any edge case handling can be centralized
to this module, allowing the command to remain (relatively) loosely bound
from the rest of Pygin's libraries.
"""

from typing import Any, Type

# Make all commands visible. This is an intentional star-import so that
# our helper functions work. Nothing from this module is actually used directly.
from src.commands import *  # noqa: F403, F401
from src.libs.argument_lib import ArgumentParser
from src.libs.command_lib import get_commands_as_dict


def execute_command(cmd_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a command by name.

    It is assumed that the arguments for this command are directly from the
    `payload` field of the `command_request` message; they do not have to be
    parsed, as this will be handled by an explicit call to ArgumentParser.

    :param cmd_name: The name of the command to invoke.
    :param args: The arguments to pass to the command.
    :returns: A dictionary result generated by the command.
    """
    # Discover the relevant command class by lookup.
    try:
        cmd_class = get_commands_as_dict()[cmd_name]
    except KeyError:
        raise RuntimeError(f"Command {cmd_name} isn't registered!")

    # Invoke the argument parser to get everything into the correct format.
    #
    # mypy complains about this property, which it incorrectly thinks will
    # return Callable[CommandBase, type[ArgumentParser]].
    parser_type: Type[ArgumentParser] = cmd_class.argument_parser  # type: ignore[assignment]
    arg_parser: ArgumentParser = parser_type()
    if not arg_parser.parse_arguments(args):
        raise RuntimeError(
            f"One or more required arguments is missing for {cmd_name} from {args=}"
        )

    # Actually execute the command and return its immediate result.
    return cmd_class.execute_command(arg_parser.get_stored_args())
