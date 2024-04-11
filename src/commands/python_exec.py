"""
Command allowing the user to execute arbitrary Python.
"""

from typing import Any, Optional, Type
import datetime
import traceback


from pydantic import BaseModel, Field, AwareDatetime

from deaddrop_meta.command_lib import CommandBase, RendererBase


class ExecArguments(BaseModel):
    """
    Simple helper class used for holding arguments.
    """

    command: str = Field(
        json_schema_extra={
            "description": "The actual Python code to execute."
        },
    )


class ExecResult(BaseModel):
    """
    Model representing the results of the exec command.
    """
    exec_timestamp: AwareDatetime = Field(
        json_schema_extra={"description": "The time at which the exec() call returned."},
    )
    success: bool = Field(
        json_schema_extra={"description": "True if no exception was raised."},
    )
    traceback: Optional[str] = Field(
        json_schema_extra={"description": "The traceback if an exception was raised."},
    )


class ExecCommand(CommandBase):
    """
    Execute arbitrary Python code. Note that this is executed in a Celery worker.
    """

    name: str = "exec"
    description: str = __doc__
    version: str = "0.0.1"
    argument_model: Type[BaseModel] = ExecArguments
    result_model: Type[BaseModel] = ExecResult

    command_renderer: Optional[Type[RendererBase]] = None

    @classmethod
    def execute_command(cls, args: dict[str, Any]) -> dict[str, Any]:
        cmd_args = ExecArguments.model_validate(args)

        # Invoke Python exec
        try:
            exec(cmd_args.command)
        except Exception:
            res = ExecResult(
                exec_timestamp=datetime.datetime.now(datetime.UTC),
                success=False,
                traceback=traceback.format_exc()
            )
            return res.model_dump()

        # Return as dictionary
        res = ExecResult(
            exec_timestamp=datetime.datetime.now(datetime.UTC),
            success=True
        )
        return res.model_dump()
