"""
Generic command to download a single file.

This command accepts a single argument, the file to download.

Take care when opening large files; the entire file is read into memory and
then converted to base64! Very inefficient. It is up to the user to fragment
the file ahead of time manually if necessary. A protocol may also perform
fragmentation if supported.

The path is resolved before the file is opened.
"""

from base64 import b64encode
from pathlib import Path
from typing import Any, Optional, Type, Union
import os

import logging
import traceback

from pydantic import BaseModel, Field, field_serializer

from deaddrop_meta.command_lib import CommandBase, RendererBase

logger = logging.getLogger(__name__)


class DownloadArguments(BaseModel):
    """
    Simple helper class used for holding arguments.
    """

    # The generated JSON schema will have type: string.
    #
    # Also, Pydantic is smart enough to turn strings into Path objects on
    # validation.
    filepath: Path = Field(
        json_schema_extra={"description": "The path to the file to download."}
    )


class DownloadResult(BaseModel):
    """
    Model representing the results of the download command.
    """

    data: Optional[bytes] = Field(
        json_schema_extra={"description": "The contents of the file."}
    )
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

    @field_serializer("data", when_used="json-unless-none")
    @classmethod
    def serialize_bytes(cls, v: bytes) -> str:
        """
        Turn bytes into their base64 representation before it pops out of a JSON file.
        """
        return b64encode(v).decode("utf-8")


class DownloadCommand(CommandBase):
    """
    Download a single file accessible to Pygin with its current permissions.
    """

    name: str = "download"
    description: str = __doc__
    version: str = "0.0.1"
    argument_model: Type[BaseModel] = DownloadArguments
    result_model: Type[BaseModel] = DownloadResult

    command_renderer: Optional[Type[RendererBase]] = None

    @classmethod
    def execute_command(cls, args: dict[str, Any]) -> dict[str, Any]:
        # there are no additional args, so we simply use the model to make
        # things more readable
        cmd_args: DownloadArguments = DownloadArguments.model_validate(args)
        cmd_args.filepath = cmd_args.filepath.resolve()

        try:
            with open(cmd_args.filepath, "rb") as fp:
                data = fp.read()

            res = DownloadResult(
                data=data,
                resolved_path=cmd_args.filepath,
                success=True,
                error=None,
                stat=cls.getstat(cmd_args.filepath),
            )
            return res.model_dump()
        except Exception:
            res = DownloadResult(
                data=None,
                resolved_path=cmd_args.filepath,
                success=False,
                error=traceback.format_exc(),
                stat=cls.getstat(cmd_args.filepath),
            )
            return res.model_dump()

    # From https://stackoverflow.com/questions/55638905/how-to-convert-os-stat-result-to-a-json-that-is-an-object
    @staticmethod
    def getstat(path: Path) -> Union[dict, None]:
        try:
            s_obj = os.stat(path)
            return {k: getattr(s_obj, k) for k in dir(s_obj) if k.startswith("st_")}
        except Exception:
            return None
