"""
Plaintext TCP-based implementation of the dddb messaging protocol.

Used for debugging, doesn't have any dependencies.
"""

from typing import Type, Any, ClassVar
import logging
import socket
import time

from pydantic import ValidationError

from deaddrop_meta.argument_lib import Argument, ArgumentType, DefaultParsers
from deaddrop_meta.protocol_lib import (
    ProtocolBase,
    ProtocolConfig,
    ProtocolArgumentParser,
    DeadDropMessage,
)

logger = logging.getLogger(__name__)


class PlaintextTCPConfig(ProtocolConfig):
    """
    Model detailing available configuration options for plaintext_tcp.
    """

    PLAINTEXT_TCP_CHECKIN_FREQUENCY: int
    PLAINTEXT_TCP_LISTEN_TIMEOUT: int
    PLAINTEXT_TCP_RECV_PORT: int
    PLAINTEXT_TCP_SEND_PORT: int
    PLAINTEXT_TCP_HOST: str

    checkin_interval_name: ClassVar[str] = "PLAINTEXT_TCP_CHECKIN_FREQUENCY"
    section_name: ClassVar[str] = "plaintext_tcp"
    dir_attrs: ClassVar[list[str]] = []  # No directories needed


class PlaintextTCPArgumentParser(ProtocolArgumentParser):
    """
    Parser for the plaintext_local configuration.
    """

    arguments: list[Argument] = [
        Argument(
            arg_type=ArgumentType.INTEGER,
            name="PLAINTEXT_TCP_CHECKIN_FREQUENCY",
            description="The frequency with which to start the TCP listener.",
            _parser=DefaultParsers.parse_integer,
        ),
        Argument(
            arg_type=ArgumentType.INTEGER,
            name="PLAINTEXT_TCP_LISTEN_TIMEOUT",
            description="The timeout duration of a single listener.",
            _parser=DefaultParsers.parse_integer,
        ),
        Argument(
            arg_type=ArgumentType.INTEGER,
            name="PLAINTEXT_TCP_RECV_PORT",
            description="The TCP port used to receieve messages.",
            _parser=DefaultParsers.parse_integer,
        ),
        Argument(
            arg_type=ArgumentType.INTEGER,
            name="PLAINTEXT_TCP_SEND_PORT",
            description="The TCP port used to send messages.",
            _parser=DefaultParsers.parse_integer,
        ),
        Argument(
            arg_type=ArgumentType.INTEGER,
            name="PLAINTEXT_TCP_HOST",
            description="The TCP host used to send and receive messages.",
            _parser=DefaultParsers.parse_integer,
        ),
    ]


class PlaintextTCPProtocol(ProtocolBase):
    """
    Plaintext implementation of the DeadDrop standard messaging system, similar
    to plaintext_local, but over TCP sockets.

    Like plaintext_local, it does not leverage an external service and has minimal
    error handling. It is as reliable as TCP itself is, and no more. It is intended
    for local testing when the filesystem cannot be used to "send" messages.

    To receive messages, this protocol listens over the specified port and accepts
    all incoming connections. It assumes that the only message sent is a valid
    plaintext DeadDrop JSON message, then immediately closes the connection.

    Because of how the agent is set up, the listener times out at regular intervals
    and returns all *valid* messages received during that time period.

    When sending messages, this protocol will attempt to connect to the target
    over the specified port (assumed to be localhost) until the message is
    successfully sent. Note that this can cause a denial of service if too many
    messages are queued because the target is offline.
    """

    name: str = "plaintext_tcp"
    description: str = __doc__
    version: str = "0.0.1"
    config_parser: Type[ProtocolArgumentParser] = PlaintextTCPArgumentParser

    @classmethod
    def send_msg(cls, msg: DeadDropMessage, args: dict[str, Any]) -> dict[str, Any]:
        # Since we don't use any arguments besides those in the configuration
        # object, we convert the argument dictionary back to the model.
        local_cfg: PlaintextTCPConfig = PlaintextTCPConfig.model_validate(args)
        host = local_cfg.PLAINTEXT_TCP_HOST
        port = local_cfg.PLAINTEXT_TCP_SEND_PORT

        # The actual bytes to be written out
        data = msg.model_dump_json().encode("utf-8")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            while True:
                try:
                    s.connect((host, port))

                    # Issue data, then tear down the connection so the other side
                    # knows we're done
                    s.sendall(data)
                    s.shutdown(socket.SHUT_RDWR)
                    s.close()

                    # Break out of infinite trial loop
                    break
                except (ConnectionRefusedError, TimeoutError):
                    logger.info(f"{host}:{port} is unreachable, retrying")
                    time.sleep(1)
                    continue

        # Arbitrary response
        return {"bytes_sent": len(data), "host": host, "port": port}

    @classmethod
    def get_new_messages(cls, args: dict[str, Any]) -> list[DeadDropMessage]:
        # Since we don't use any arguments besides those in the configuration
        # object, we convert the argument dictionary back to the model.
        local_cfg: PlaintextTCPConfig = PlaintextTCPConfig.model_validate(args)

        # Bit of an odd pattern. What we're going to do is set up the listener
        # for the specified duration, accept all messages that come our way,
        # and return the result. The architecture was not really built around
        # direct, real-time communication, so this is why we don't just keep
        # a listener around forever.
        #
        # Because this is all "internal" and for testing only, we make the assumption
        # that clients are kind enough to close the connection so we don't need to
        # include the length of the message with the message itself. In general,
        # it's assumed that one connection = one message; multiple messages must
        # be sent by repeatedly opening ocnnections.
        #
        # see https://stackoverflow.com/questions/2444178/how-to-make-socket-listen1-work-for-some-time-and-then-continue-rest-of-code
        result: list[DeadDropMessage] = []

        host = local_cfg.PLAINTEXT_TCP_HOST
        port = local_cfg.PLAINTEXT_TCP_RECV_PORT

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            start_time = time.time()

            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # This sets an absolute limit on blocking operations, but is not
            # the primary form of guaranteeing this operates for a short period
            # of time
            s.settimeout(local_cfg.PLAINTEXT_TCP_LISTEN_TIMEOUT)
            s.bind((host, port))
            s.listen()
            while True:
                # Accept connections
                try:
                    client, _ = s.accept()
                except TimeoutError:
                    break

                # Get all data
                data = b""
                while True:
                    new_data = client.recv(1024)
                    if not new_data:
                        break
                    data += new_data

                # Assume utf-8 encoding and JSON, attempt to convert to message
                try:
                    result.append(DeadDropMessage.model_validate_json(data))
                except ValidationError as e:
                    logger.error(
                        f"Failed to convert {repr(data)} to a DeadDropMessage, ignoring message: {e}"
                    )

                # Only evaluate the timeout period after the client disconnects
                # to prevent accidentally disconnecting earlier
                if time.time() - start_time >= local_cfg.PLAINTEXT_TCP_LISTEN_TIMEOUT:
                    break

        return result
