"""
This implements the command dispatch module as described in DeadDrop's
generic architecture model for agents.
"""

from typing import Any

# Make all protocols visible. This is an intentional star-import so that
# our helper functions work.
from src.commands import *

from src.agent_code import config
from src.libs import command_lib

def execute_command(
    cmd_name: str,
    args: dict[str, Any]
) -> dict[str, Any]:
    """
    Execute a command by name.
    
    It is assumed that the arguments for this command are directly from the
    `payload` field of the `command_request` message; they do not have to be
    parsed, as this will be handled by an explicit call to ArgumentParser.
    
    :param cmd_name: The name of the command to invoke.
    :param args: The arguments to pass to the command.
    """
    # Discover the relevant command class by lookup.
    
    # Invoke the argument parser to get everything into the correct format.
    
    # Actually execute the command and return its immediate result.
    raise NotImplementedError