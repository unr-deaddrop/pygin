"""
Allows a user to write a file to disk from a server.
"""

from base64 import b64decode
from pathlib import Path
from typing import Any, Optional, Type, Union
import os

import logging
import traceback

from pydantic import BaseModel, Field, field_validator

from deaddrop_meta.command_lib import CommandBase, RendererBase
from deaddrop_meta.protocol_lib import File, FileData

logger = logging.getLogger(__name__)


class UploadArguments(BaseModel):
    """
    Simple helper class used for holding arguments.
    """

    # The generated JSON schema will have type: string.
    #
    # Also, Pydantic is smart enough to turn strings into Path objects on
    # validation.
    filepath: Path = Field(
        json_schema_extra={"description": "The path to write this file to. Resolved at runtime."}
    )

    data: bytes = Field(
        json_schema_extra={"description": "The actual file to write."}
    )

    @field_validator(
        "data",
        mode="before",
    )
    @classmethod
    def validate_base64(cls, v: Any) -> Union[bytes, None]:
        """
        If the file data is not bytes, assume base64.
        """
        if v is None or isinstance(v, bytes):
            return v

        try:
            val = b64decode(v)
        except Exception as e:
            raise ValueError(f"Assumed b64decode of {v} failed.") from e

        return val


class UploadResult(BaseModel):
    """
    Model representing the results of the download command.
    """

    success: bool = Field(
        json_schema_extra={"description": "Whether the file could be opened and read."}
    )
    error: Optional[str] = Field(
        json_schema_extra={"description": "If unsuccessful, the OSError."}
    )
    resolved_path: Optional[Path] = Field(
        json_schema_extra={"description": "The absolute, resolved path of the file."}
    )
    stat: Optional[dict[str, Any]] = Field(
        json_schema_extra={
            "description": "Additional file information obtained from os.stat()."
        }
    )



class UploadCommand(CommandBase):
    """
    Download a single file accessible to Pygin with its current permissions.
    """

    name: str = "upload"
    description: str = __doc__
    version: str = "0.0.1"
    argument_model: Type[BaseModel] = UploadArguments
    result_model: Type[BaseModel] = UploadResult

    command_renderer: Optional[Type[RendererBase]] = None

    @classmethod
    def execute_command(cls, args: dict[str, Any]) -> dict[str, Any]:
        # there are no additional args, so we simply use the model to make
        # things more readable
        cmd_args: UploadArguments = UploadArguments.model_validate(args)
        cmd_args.filepath = cmd_args.filepath.resolve()

        try:
            with open(cmd_args.filepath, "wb+") as fp:
                fp.write(cmd_args.data)
        except Exception:
            res = UploadResult(
                resolved_path=cmd_args.filepath,
                success=False,
                error=traceback.format_exc(),
                stat=None,
            )
            return res.model_dump()
        
        res = UploadResult(
            resolved_path=cmd_args.filepath,
            success=True,
            error=None,
            stat=cls.getstat(cmd_args.filepath),
        )

    # From https://stackoverflow.com/questions/55638905/how-to-convert-os-stat-result-to-a-json-that-is-an-object
    @staticmethod
    def getstat(path: Path) -> Union[dict, None]:
        try:
            s_obj = os.stat(path)
            return {k: getattr(s_obj, k) for k in dir(s_obj) if k.startswith("st_")}
        except Exception:
            return None

