"""
Command implementing simple directory listing, including a renderer.

The main purpose of this command is to demonstrate a basic command renderer.
"""

from typing import Any, Optional, Type
from pathlib import Path
import os

from pydantic import BaseModel, Field

from deaddrop_meta.command_lib import CommandBase, RendererBase


class ListDirArguments(BaseModel):
    """
    Argument class for the kill command.
    """

    path: str = Field(
        json_schema_extra={"description": "The path to evaluate, resolved at runtime."},
    )


class ListDirResult(BaseModel):
    """
    Returns the system directory structure rooted at `path` as a nested dictionary.
    """

    result: dict[str, Any] = Field(
        json_schema_extra={"description": "The recursive result."},
    )


def recurse_dir(path: str) -> dict[str, Any]:
    # https://stackoverflow.com/questions/58702587/python-create-a-dictionary-from-a-folder-directories
    resolved_path = str(Path(path).resolve())
    for root, dirs, files in os.walk(resolved_path):
        tree = {"name": root, "type": "folder", "children": []}

        # mypy doesn't recognize tree["children"] as a list
        assert isinstance(tree["children"], list)

        tree["children"].extend([recurse_dir(os.path.join(root, d)) for d in dirs])
        tree["children"].extend(
            [{"name": os.path.join(root, f), "type": "file"} for f in files]
        )
    return tree


class ListDirCommand(CommandBase):
    """
    Recursively iterate a directory, returning the result as a dictionary.
    """

    name: str = "list_dir"
    description: str = __doc__
    version: str = "0.0.1"
    argument_model: Type[BaseModel] = ListDirArguments
    result_model: Type[BaseModel] = ListDirResult

    command_renderer: Optional[Type[RendererBase]] = None

    @classmethod
    def execute_command(cls, args: dict[str, Any]) -> dict[str, Any]:
        cmd_args = ListDirArguments.model_validate(args)

        res = ListDirResult(result=recurse_dir(cmd_args.path))
        return res.model_dump()
