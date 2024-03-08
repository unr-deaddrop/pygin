"""
These tests assert that messages for specific commands are parsed as expected.
This asserts two things:
- previously valid messages do not suddenly become unreadable
- the high-level command executes as expected and returns a valid result
"""

from pathlib import Path
from datetime import datetime

from deaddrop_meta.protocol_lib import DeadDropMessage

from src.agent_code.command_dispatch import execute_command
from src.commands.ping import PingArguments, PingResult


class TestClass:
    def test_ping(self):
        """
        codeauthor:: Lloyd Gonzales <lgonzalesna@gmail.com>

        Check that the ping command functions as expected.

        This tests the following requirements for the ping command:
        - The ping command shall preserve and return the timestamp of the
          command request.
        - The ping command shall include the time of execution as part of the
          result.
        - The ping command shall echo the message specified by the user if one
          was provided.
        """
        # Load the raw command_request message
        DOCUMENT = Path("./tests/resources/test_ping.json")
        with open(DOCUMENT, "rt") as fp:
            msg = DeadDropMessage.model_validate_json(fp.read())

        # Execute the message as parsed by the library
        result = PingResult.model_validate(
            execute_command(msg.payload.cmd_name, msg.payload.cmd_args)
        )

        # Assert that the response contains all of the following:
        # - a ping_timestamp, equal to "ping"
        # - a pong_timestamp that is greater than ping_timestamp and is within
        #   10 seconds of the current time of the test (if this takes more than
        #   a quarter of a second to execute, we have bigger problems)
        # - the expected echo message
        args = PingArguments.model_validate(msg.payload.cmd_args)

        # Check that the ping timestamp is equal to the original timestamp
        assert result.ping_timestamp == args.ping_timestamp

        # Check that the pong timestamp is greater than that of the "base" message.
        # This is valid check provided that the system time is correct, since
        # all timestamps are assumed to be UTC.
        assert result.pong_timestamp.timestamp() > args.ping_timestamp.timestamp()

        # Assert that the listed pong timestamp is within 10 seconds of true time.
        assert (datetime.utcnow().timestamp() - result.pong_timestamp.timestamp()) <= 10

        # Assert that the user's message, if any, was echoed back.
        assert result.message == args.message
