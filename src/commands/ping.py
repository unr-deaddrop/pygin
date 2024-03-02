"""
Implements the ping command.
"""

from typing import Any, Optional, Type
import time
from datetime import datetime

from pydantic import BaseModel

from deaddrop_meta.argument_lib import (
    DefaultParsers,
    ArgumentParser,
    ArgumentType,
    Argument,
)
from deaddrop_meta.command_lib import CommandBase, RendererBase


class PingArguments(BaseModel):
    """
    Simple helper class used for holding arguments.

    Although PingArgumentParser will guarantee that our dictionary has the
    same keys in the right format as our attributes below, using a Pydantic
    model adds an extra layer of safety in case something *does* go wrong
    somewhere.
    """

    message: str = ""
    delay: float = 0
    ping_timestamp: float


class PingArgumentParser(ArgumentParser):
    """
    Parser for the ping command.
    """

    arguments: list[Argument] = [
        Argument(
            arg_type=ArgumentType.STRING,
            name="message",
            description="Extra message to include in the ping response.",
            required=False,
            is_iterable=False,
            _parser=DefaultParsers.parse_string,
        ),
        Argument(
            arg_type=ArgumentType.FLOAT,
            name="delay",
            description="The number of seconds to delay the reponse for.",
            required=False,
            is_iterable=False,
            default=0,
            _parser=DefaultParsers.parse_float,
        ),
        Argument(
            arg_type=ArgumentType.FLOAT,
            name="ping_timestamp",
            description="The reference timestamp for the ping request.",
            required=True,
            is_iterable=False,
            _parser=DefaultParsers.parse_float,
        ),
    ]


class PingCommand(CommandBase):
    """
    Simple test command used to evaluate connectivity.

    Ping accepts two optional arguments:
    - A delay before sending the response, in seconds (0 by default)
    - A message to return with the response (nothing by default)

    The structure of the payload is as follows:
    ```json
    {
        // The time at which the ping was issued.
        "ping_timestamp": 000000000
        // The time at which the ping was received.
        "pong_timestamp": 000000000
        // The optional message included with the original ping.
        "message": str
    }
    ```
    """

    name: str = "ping"
    description: str = __doc__
    version: str = "0.0.1"
    argument_parser: Type[ArgumentParser] = PingArgumentParser

    command_renderer: Optional[Type[RendererBase]] = None

    @classmethod
    def execute_command(cls, args: dict[str, Any]) -> dict[str, Any]:
        # ping is simple, and therefore we can use a helper class to
        # validate the args and provide attributes
        cmd_args = PingArguments.model_validate(args)

        # Sleep as desired
        time.sleep(cmd_args.delay)

        # Construct the dictionary response
        return {
            "ping_timestamp": cmd_args.ping_timestamp,
            "pong_timestamp": datetime.utcnow().timestamp(),
            "message": cmd_args.message,
        }
