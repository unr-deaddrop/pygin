"""
Clean up all resources used by the agent and start the shutdown process.
"""

from typing import Any, Optional, Type
import datetime
import shlex
import subprocess


from pydantic import BaseModel, Field, AwareDatetime

from deaddrop_meta.command_lib import CommandBase, RendererBase


class KillArguments(BaseModel):
    """
    Argument class for the kill command.
    """

    delay_time: int = Field(
        default=60,
        json_schema_extra={
            "description": "The time between returning a result and killing the agent."
        },
    )


class KillResult(BaseModel):
    """
    Returns nothing.
    """

    scheduled_kill_time: AwareDatetime = Field(
        json_schema_extra={
            "description": "The time at which the kill operation is expected to complete."
        },
    )


class KillCommand(CommandBase):
    """
    Kill the agent after a short delay, but independently of the command returning.
    """

    name: str = "kill"
    description: str = __doc__
    version: str = "0.0.1"
    argument_model: Type[BaseModel] = KillArguments
    result_model: Type[BaseModel] = KillResult

    command_renderer: Optional[Type[RendererBase]] = None

    @classmethod
    def execute_command(cls, args: dict[str, Any]) -> dict[str, Any]:
        cmd_args = KillArguments.model_validate(args)

        target_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            seconds=cmd_args.delay_time
        )

        # In the background, invoke the process (which allows this to return
        # and allows the control unit to send back acknowledgement)
        subprocess.Popen(
            shlex.split(f"python -m src.agent_code.stop_agent {cmd_args.delay_time}")
        )

        res = KillResult(scheduled_kill_time=target_time)
        return res.model_dump()
