"""
Command exposing generic shell commands. Allows the user to execute a single
non-interactive command.
"""

from typing import Any, Optional, Type
from datetime import datetime
import logging
import shlex
import subprocess
import traceback

from pydantic import BaseModel

from deaddrop_meta.argument_lib import (
    DefaultParsers,
    ArgumentParser,
    ArgumentType,
    Argument,
)
from deaddrop_meta.command_lib import CommandBase, RendererBase

logger = logging.getLogger(__name__)


class ShellArguments(BaseModel):
    """
    Simple helper class used for holding arguments.
    """

    command: str
    use_shell: bool
    timeout: Optional[int] = None


class ShellArgumentParser(ArgumentParser):
    """
    Parser for the shell command.
    """

    arguments: list[Argument] = [
        Argument(
            arg_type=ArgumentType.STRING,
            name="command",
            description="The command to execute.",
            required=True,
            is_iterable=False,
            _parser=DefaultParsers.parse_string,
        ),
        Argument(
            arg_type=ArgumentType.BOOLEAN,
            name="use_shell",
            description="Whether to use `shell=True`. If True, this does not use `shlex.split()`.",
            required=True,
            is_iterable=False,
            _parser=DefaultParsers.parse_float,
        ),
        Argument(
            arg_type=ArgumentType.INTEGER,
            name="timeout",
            description="The timeout for the command; returns an empty result on failure.",
            required=False,
            is_iterable=False,
            default=None,
            _parser=DefaultParsers.parse_integer,
        ),
    ]


class ShellCommand(CommandBase):
    """
    Generic command to execute arbitrary shell commands.

    Shell accepts three arguments:
    - The command to execute
    - Whether to use a shell as the execution environment (i.e. shell=True)
    - The timeout for the command

    The structure of the payload is as follows:
    ```json
    {
        // Whether or not subprocess.run() completed without raising an
        // exception. For example, attempting to execute a binary that does
        // not exist when shell=False will raise FileNotFoundError.
        "success": bool,
        // The exception raised if success=False. Empty string if no exception
        // was raised.
        "exception": str,
        // The stdout of the command. Empty string if an exception was raised.
        "stdout": str,
        // The stderr of the command. Empty string if an exception was raised.
        "stderr": str,
        // The return code. -1 if an exception was raised.
        "returncode": int,
        // Whether or not shell=True was used.
        "shell": bool,
        // The start and end time of the command.
        "start_time": float
        "finish_time": float
    }
    ```
    """

    name: str = "shell"
    description: str = __doc__
    version: str = "0.0.1"
    argument_parser: Type[ArgumentParser] = ShellArgumentParser

    command_renderer: Optional[Type[RendererBase]] = None

    @classmethod
    def execute_command(cls, args: dict[str, Any]) -> dict[str, Any]:
        # there are no additional args, so we simply use the model to make
        # things more readable
        cmd_args: ShellArguments = ShellArguments.model_validate(args)

        logger.debug(
            f"Executing {cmd_args.command} with shell={cmd_args.use_shell}, timeout={cmd_args.timeout} "
        )
        start_time = datetime.utcnow().timestamp()
        if cmd_args.use_shell:
            # If shell=True, we don't use shlex to parse the input since it's
            # unnecessary.
            try:
                p = subprocess.run(
                    cmd_args.command,
                    capture_output=True,
                    shell=True,
                    timeout=cmd_args.timeout,
                )
                return cls.parse_process_result(p, cmd_args, start_time)
            except Exception:
                return cls.parse_exception_result(
                    traceback.format_exc(), cmd_args, start_time
                )

        try:
            shell_args = shlex.split(cmd_args.command)
            logger.debug(f"Splitting {cmd_args.command} -> {shell_args}")
            p = subprocess.run(
                shell_args, capture_output=True, shell=False, timeout=cmd_args.timeout
            )
            return cls.parse_process_result(p, cmd_args, start_time)
        except Exception:
            return cls.parse_exception_result(
                traceback.format_exc(), cmd_args, start_time
            )

    @staticmethod
    def parse_process_result(
        p: subprocess.CompletedProcess, cmd_args: ShellArguments, start_time: float
    ) -> dict[str, Any]:
        return {
            "success": True,
            "exception": "",
            "stdout": p.stdout,
            "stderr": p.stderr,
            "returncode": p.returncode,
            "shell": cmd_args.use_shell,
            "start_time": start_time,
            "end_time": datetime.utcnow().timestamp(),
        }

    @staticmethod
    def parse_exception_result(
        traceback_str: str, cmd_args: ShellArguments, start_time: float
    ) -> dict[str, Any]:
        return {
            "success": False,
            "exception": traceback_str,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "shell": cmd_args.use_shell,
            "start_time": start_time,
            "end_time": datetime.utcnow().timestamp(),
        }
