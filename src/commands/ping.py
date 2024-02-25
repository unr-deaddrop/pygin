"""
Implements the ping command.
"""

from typing import Any, Optional, Type

from src.libs.cmd_lib import (
    DefaultParsers,
    CommandBase,
    ArgumentParser,
    ArgumentType,
    Argument,
    RendererBase,
)


class PingArgumentParser(ArgumentParser):
    """
    Parser for the ping command.
    """

    arguments: list[Argument] = [
        Argument(
            cmd_type=ArgumentType.STRING,
            name="message",
            description="Extra message to include in the ping response.",
            required=False,
            is_iterable=False,
            _parser=DefaultParsers.parse_string,
        ),
        Argument(
            cmd_type=ArgumentType.FLOAT,
            name="delay",
            description="The number of seconds to delay the reponse for.",
            required=False,
            is_iterable=False,
            default=0,
            _parser=DefaultParsers.parse_integer,
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
        raise NotImplementedError
