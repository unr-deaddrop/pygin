"""
Runs Empyrean.

This is the subprocess version, which is intentionally less well-structured.
"""

from typing import Any, Optional, Type
import logging
from pathlib import Path
import subprocess
import sys

from pydantic import BaseModel, Field

from deaddrop_meta.command_lib import CommandBase, RendererBase


logger = logging.getLogger(__name__)

# A list of all paths where the Empyrean executable may be found.
FALLBACK_PATHS = [
    Path("./contribs/empyrean/main.exe"),
    Path("./contribs/empyrean/empyrean.exe"),
    Path("empyrean.exe")
]
OUTPUT_FILE = "./empyrean-result.json"

class EmpyreanExecArguments(BaseModel):
    """
    Simple helper class used for holding arguments.
    """

    empyrean_path: Path = Field(
        default=Path("./contribs/empyrean/main.exe"),
        json_schema_extra={
            "description": "The path to the Empyrean executable."
        }
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
    message: Optional[str] = Field(
        json_schema_extra={"description": "Any additional status message."},
    )
    output: dict[str, Any] = Field(
        json_schema_extra={
            "description": "The complete, parsed output of running Empyrean."
        },
    )


class EmpyreanExecCommand(CommandBase):
    """
    Invoke Emyprean at the Pygin level (i.e. as Pygin code).

    Windows-only. This command will return empty outputs
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

        # if sys.platform != "win32":
        if False:
            return cls.return_invalid_os()
        else:
            # Add the selected path to the list of fallbacks.
            search_paths: list[Path] = [cmd_args.empyrean_path] + FALLBACK_PATHS
            for path in search_paths:
                if not path.exists():
                    logger.info(f"{path} does not exist")
                    continue
                
                p = subprocess.run([path.resolve()], capture_output=True)
                msg = f"{p.stdout=} {p.stderr=}"
                
                if not OUTPUT_FILE.exists():
                    return cls.return_missing_output(msg)
                
                
                
        
            return cls.return_missing_exe()

    @staticmethod
    def return_missing_output(msg: str) -> dict[str, Any]:
        """
        When the executable cannot be found, complain.
        """
        result = EmpyreanExecResult(
            success=False,
            message="empyrean-result.json missing.",
            output={
                "output": msg
            }
        )

        return result.model_dump()  
                
    @staticmethod
    def return_missing_exe() -> dict[str, Any]:
        """
        When the executable cannot be found, complain.
        """
        result = EmpyreanExecResult(
            success=False,
            message="Could not find the Empyrean executable.",
            output={}
        )

        return result.model_dump()                

    @staticmethod
    def return_invalid_os() -> dict[str, Any]:
        """
        When this is run on a non-Windows environment, this does nothing.
        """
        result = EmpyreanExecResult(
            success=False,
            message="Pygin was running on a non-Windows environment.",
            output={}
        )

        return result.model_dump()

    def return_parsed_result(msg: str) -> dict[str, Any]:
        """
        Nominal case.
        """
        result = EmpyreanExecResult(
            success=False,
            message="empyrean-result.json missing.",
            output={
                "output": msg
            }
        )

        return result.model_dump()  