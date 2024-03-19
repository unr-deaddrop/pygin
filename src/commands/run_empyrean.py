"""
Runs Empyrean.

This is the Python native version.
"""

from typing import Any, Optional, Type
import logging

from pydantic import BaseModel, Field, AwareDatetime

from deaddrop_meta.command_lib import CommandBase, RendererBase

logger = logging.getLogger(__name__)


class EmpyreanArguments(BaseModel):
    """
    Simple helper class used for holding arguments.
    """
    exec_browser: bool = Field(
        default=True,
        json_schema_extra={
            "description": "Whether to run the browser module."
        }
    )
    exec_discord: bool = Field(
        default=True,
        json_schema_extra={
            "description": "Whether to run the Discord module."
        }
    )
    exec_sysinfo: bool = Field(
        default=True,
        json_schema_extra={
            "description": "Whether to run the system info module."
        }
    )


class EmpyreanResult(BaseModel):
    """
    Model representing the results of the shell command.
    """

    success: bool = Field(
        json_schema_extra={
            "description": (
                "Whether or not Empyrean ran. False if not on Windows, or if the"
                " executable was murdered before it could be run."
            )
        },
    )
    browser_output: dict[str, Any] = Field(
        json_schema_extra={
            "description": (
                "Output of the browser module. Note that credentials are not currently"
                " extracted."
            )
        },
    )


class EmpyreanCommand(CommandBase):
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

    name: str = "empyrean"
    description: str = __doc__
    version: str = "0.0.1"
    argument_model: Type[BaseModel] = EmpyreanArguments
    result_model: Type[BaseModel] = EmpyreanResult

    command_renderer: Optional[Type[RendererBase]] = None

    @classmethod
    def execute_command(cls, args: dict[str, Any]) -> dict[str, Any]:
        return {}
