"""
Plaintext TCP-based implementation of the dddb messaging protocol.

Used for debugging, doesn't have any dependencies.
"""

from typing import Type, Any, ClassVar
import logging
import socket
import time
import errno

from pydantic import Field, ValidationError

from deaddrop_meta.protocol_lib import (
    ProtocolBase,
    ProtocolConfig,
    DeadDropMessage,
)
from deaddrop_meta.interface_lib import EndpointMessagingData

logger = logging.getLogger(__name__)


class PlaintextTCPConfig(ProtocolConfig):
    """
    Model detailing available configuration options for plaintext_tcp.
    """

    PLAINTEXT_TCP_CHECKIN_FREQUENCY: int = Field(
        default=10,
        json_schema_extra={
            "description": "The frequency with which to start the TCP listener."
        },
    )
    PLAINTEXT_TCP_LISTEN_TIMEOUT: int = Field(
        default=8,
        json_schema_extra={"description": "The timeout duration of a single listener."},
    )

    PLAINTEXT_TCP_LISTEN_BIND_HOST: str = Field(
        default="0.0.0.0",
        json_schema_extra={
            "description": "The host to bind to when setting up any listener."
        },
    )
    PLAINTEXT_TCP_LISTEN_RECV_PORT: int = Field(
        default=12345,
        json_schema_extra={
            "description": "The port to bind to when receiving messages."
        },
    )
    PLAINTEXT_TCP_LISTEN_SEND_PORT: int = Field(
        default=12346,
        json_schema_extra={
            "description": "The port to bind to when sending messages via a listener."
        },
    )

    # Debug/server only
    PLAINTEXT_TCP_INITIATE_RECV_HOST: str = Field(
        default="localhost",
        json_schema_extra={
            "description": "When receiving messages by initiating a connection, the host to connect to."
        },
    )
    PLAINTEXT_TCP_INITIATE_RECV_PORT: int = Field(
        default=12346,
        json_schema_extra={
            "description": "When receiving messages by initiating a connection, the port to connect to."
        },
    )
    PLAINTEXT_TCP_INITIATE_RETRY_COUNT: int = Field(
        default=120,
        json_schema_extra={
            "description": "When receiving messages by initiating a connection, the number of times to attempt to connect."
        },
    )

    PLAINTEXT_TCP_USE_LISTENER_TO_RECV: bool = Field(
        default=True,
        json_schema_extra={
            "description": "Whether to receive messages via a listener."
        },
    )
    PLAINTEXT_TCP_USE_LISTENER_TO_SEND: bool = Field(
        default=True,
        json_schema_extra={"description": "Whether to send messages via a listener."},
    )
    PLAINTEXT_TCP_INITIATE_SEND_HOST: str = Field(
        default="localhost",
        json_schema_extra={
            "description": "The target host when sending messages by initiating connections."
        },
    )
    PLAINTEXT_TCP_INITIATE_SEND_PORT: int = Field(
        default=12346,
        json_schema_extra={
            "description": "The target port when sending messages by initiating connections."
        },
    )

    checkin_interval_name: ClassVar[str] = "PLAINTEXT_TCP_CHECKIN_FREQUENCY"
    section_name: ClassVar[str] = "plaintext_tcp"
    dir_attrs: ClassVar[list[str]] = []  # No directories needed

    def convert_to_server_config(
        self, endpoint: EndpointMessagingData
    ) -> "PlaintextTCPConfig":
        # Make deep copy of current config
        new_cfg = self.model_copy(deep=True)

        # The agent always listens to receive messages. In turn, to send a message
        # by initiating, we need to disable using the listener to send, and we also
        # need to update the port/host combo.
        #
        # The host is not known to the agent itself, so it must be pulled from the
        # model; the port *is* known, and we can just switch it around.
        logger.info(
            "Setting up server to initiate a connection to"
            f" {endpoint.address}:{self.PLAINTEXT_TCP_LISTEN_RECV_PORT}"
        )
        new_cfg.PLAINTEXT_TCP_USE_LISTENER_TO_SEND = False
        new_cfg.PLAINTEXT_TCP_INITIATE_SEND_HOST = endpoint.address
        new_cfg.PLAINTEXT_TCP_INITIATE_SEND_PORT = self.PLAINTEXT_TCP_LISTEN_RECV_PORT

        # When containerized, the agent uses a listener to send. But when standalone,
        # it's up to the agent to decide what it wants to do.
        if self.PLAINTEXT_TCP_USE_LISTENER_TO_SEND:
            logger.info(
                "Agent is configured to use listeners to send messages,"
                " configuring to initiate connections to"
                f" {endpoint.address}:{self.PLAINTEXT_TCP_LISTEN_SEND_PORT}"
            )
            # If the agent is using a listener to send, this means that we need
            # to be using an initiator to receive.
            new_cfg.PLAINTEXT_TCP_USE_LISTENER_TO_RECV = False

            # Only we know the host, so this must be taken from the model.
            # However, the port to connect to is determined by the port
            # bound when sending.
            new_cfg.PLAINTEXT_TCP_INITIATE_RECV_HOST = endpoint.address
            new_cfg.PLAINTEXT_TCP_INITIATE_RECV_PORT = (
                self.PLAINTEXT_TCP_LISTEN_SEND_PORT
            )
        else:
            logger.info(
                "Agent is configured to initiate connections to send messages,"
                f"binding to 0.0.0.0:{self.PLAINTEXT_TCP_INITIATE_SEND_PORT}"
            )
            # If the agent is initiating connections to send, this means that we
            # need to be listening to receive.
            new_cfg.PLAINTEXT_TCP_USE_LISTENER_TO_RECV = True

            # In this case, the agent knows the host/port combination it needs
            # to reach out to in order to contact the server, so all we need to
            # do is listen to all interfaces on the specified port.
            new_cfg.PLAINTEXT_TCP_LISTEN_BIND_HOST = "0.0.0.0"
            new_cfg.PLAINTEXT_TCP_LISTEN_RECV_PORT = (
                self.PLAINTEXT_TCP_INITIATE_SEND_PORT
            )

        logger.info(f"Agent configuration:{self}")
        logger.info(f"Server configuration:{new_cfg}")
        return new_cfg


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

    Sending messages is a little more complicated.

    Pygin's architecture was not really built to support sustained connections,
    even though those are certainly much more efficient and normal than our
    "dead drops". The net result is that we have to make a bunch of workarounds
    to make sure Pygin reliably works with TCP.

    The main challenge is networking; when running directly on a host (or when
    running in a container with host networking), it's fairly safe to assume
    that we can listen on localhost and take over ports. However, networking
    changes when we use Docker and try to forward TCP ports out; you now
    need to bind to 0.0.0.0 to allow Docker to correctly forward ports, so
    binding to localhost no longer works.

    The impact of this is that it's no longer possible for us to just repeatedly
    send messages to localhost:8080 until the server starts listening for them;
    not only do we not know where the server is, we can't even connect to it
    unless it's either in the same container environment as us or we do a lot
    of set up to get this to work.

    So the solution is to allow Pygin to instantiate connections when it holds
    that we can use localhost to connect to the server, and set up listeners
    instead when this does not hold and the server must directly connect to the
    agent. The server should track of the agent's IP address, so it makes a little
    more sense for the burden to be on the server in this case.
    """

    name: str = "plaintext_tcp"
    description: str = __doc__
    version: str = "0.0.1"
    config_model: Type[ProtocolConfig] = PlaintextTCPConfig

    @classmethod
    def send_msg(cls, msg: DeadDropMessage, args: dict[str, Any]) -> dict[str, Any]:
        local_cfg: PlaintextTCPConfig = PlaintextTCPConfig.model_validate(args)

        if local_cfg.PLAINTEXT_TCP_USE_LISTENER_TO_SEND:
            return cls.send_msg_by_listening(msg, args)

        return cls.send_msg_by_initiating(msg, args)

    @classmethod
    def get_new_messages(cls, args: dict[str, Any]) -> list[DeadDropMessage]:
        local_cfg: PlaintextTCPConfig = PlaintextTCPConfig.model_validate(args)

        if local_cfg.PLAINTEXT_TCP_USE_LISTENER_TO_RECV:
            return cls.recv_msg_by_listening(args)

        return cls.recv_msg_by_initiating(args)

    @staticmethod
    def send_msg_by_initiating(msg, args: dict[str, Any]) -> dict[str, Any]:
        """
        Send a message by initiating a connection to a known outbound host.

        From a Celery perspective, every outgoing message essentially manifests
        itself as a task that tries to start a connection with the target host/port;
        if it fails, it keeps retrying. This effectively guarantees that all
        messages are sent, even if the host is currently unreachable.

        The advantage of this method is that the message send and receive
        implementations are symmetric; you can copy this over to the server
        and it'll work. However, it requires that you know the full host
        and port of your target ahead of time (and that it is accessible).
        """
        local_cfg: PlaintextTCPConfig = PlaintextTCPConfig.model_validate(args)
        host = local_cfg.PLAINTEXT_TCP_INITIATE_SEND_HOST
        port = local_cfg.PLAINTEXT_TCP_INITIATE_SEND_PORT

        # The actual bytes to be written out
        data = msg.model_dump_json().encode("utf-8")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            while True:
                try:
                    s.connect((host, port))
                    logger.debug(f"Connected to {host}:{port}")

                    # Issue data, then tear down the connection so the other side
                    # knows we're done
                    s.sendall(data)
                    logger.debug(f"Sent {len(data)} bytes")
                    s.shutdown(socket.SHUT_RDWR)
                    s.close()
                    logger.debug("Closed connection")

                    # Break out of infinite trial loop
                    break
                except (ConnectionRefusedError, TimeoutError):
                    logger.info(f"{host}:{port} is unreachable, retrying")
                    time.sleep(5)
                    continue

        # Arbitrary response
        return {"bytes_sent": len(data), "host": host, "port": port}

    @staticmethod
    def send_msg_by_listening(msg, args: dict[str, Any]) -> dict[str, Any]:
        """
        Send a message by waiting for an incoming connection.

        From a Celery perspective, every outgoing message manifests itself as
        a task that tries to bind to the configured port as a listener,
        sending the message as soon as it receives a connection. If multiple
        messages are sent in sequence, they wait until the port is free.

        This requires that the server (or whatever entity is receiving the
        messages) repeatedly reconnect to the agent on the configured port
        to get all messages. If the agent is not listening on that port,
        it can be assumed that all messages were

        This has the advantage of not requiring the agent to know the address
        of the server ahead of time, avoiding the issue of hardcoding
        """
        # Since we don't use any arguments besides those in the configuration
        # object, we convert the argument dictionary back to the model.
        local_cfg: PlaintextTCPConfig = PlaintextTCPConfig.model_validate(args)

        # The actual bytes to be written out
        data = msg.model_dump_json().encode("utf-8")

        host = local_cfg.PLAINTEXT_TCP_LISTEN_BIND_HOST
        port = local_cfg.PLAINTEXT_TCP_LISTEN_SEND_PORT

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Note that SO_REUSEPORT is a thing as well, but I haven't seen
            # as many examples using it so I'm avoiding it
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(local_cfg.PLAINTEXT_TCP_LISTEN_TIMEOUT)

            while True:
                try:
                    logger.debug(f"Attempting to bind to {host}:{port}")
                    s.bind((host, port))
                    s.listen()
                    break
                except OSError as e:
                    # Check if it's actually because the port is bound and not
                    # for some other reason
                    if e.errno != errno.EADDRINUSE:
                        raise RuntimeError("Unexpected OSError, failing") from e

                    # Another task is likely waiting to send its message and
                    # is listening for the server to start a connection, so
                    # wait a while
                    logger.debug(f"{host}:{port} is taken, waiting 5 seconds")
                    time.sleep(5)

            # The port is now bound, so we can wait until someone connects to us
            # (note that this goes *forever*!)
            while True:
                # Accept connections
                try:
                    client, addr = s.accept()
                    logger.debug(f"Got connection from {addr}")
                except TimeoutError:
                    continue

                # Issue data, then tear down the connection so the other side
                # knows we're done
                client.sendall(data)
                logger.debug(f"Sent {len(data)} bytes")
                client.shutdown(socket.SHUT_RDWR)
                client.close()
                logger.debug("Closed connection to client")

                # Also close our listener in the hopes that another task can
                # get to use it *soon*
                s.close()
                logger.debug("Closed listener, should be free soon")

                # Arbitrary response
                return {"bytes_sent": len(data), "host": host, "port": port}

    @classmethod
    def recv_msg_by_initiating(cls, args: dict[str, Any]) -> list[DeadDropMessage]:
        """
        Unused routine to receive messages by initiating.

        This connects to the target host and port repeatedly until it is no
        longer reachable, at which point it is assumed that all messages
        have been received.

        By default, this uses the same arguments as are used for
        `send_msg_by_listening`.
        """
        # Since we don't use any arguments besides those in the configuration
        # object, we convert the argument dictionary back to the model.
        local_cfg: PlaintextTCPConfig = PlaintextTCPConfig.model_validate(args)

        host = local_cfg.PLAINTEXT_TCP_INITIATE_RECV_HOST
        port = local_cfg.PLAINTEXT_TCP_INITIATE_RECV_PORT

        result: list[DeadDropMessage] = []

        attempts = local_cfg.PLAINTEXT_TCP_INITIATE_RETRY_COUNT

        while True:
            if attempts <= 0:
                logger.warning(
                    f"{local_cfg.PLAINTEXT_TCP_INITIATE_RETRY_COUNT} attempts expired, returning {len(result)} msgs"
                )
                break

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    # Note that SO_REUSEPORT is a thing as well, but I haven't seen
                    # as many examples using it so I'm avoiding it
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.settimeout(local_cfg.PLAINTEXT_TCP_LISTEN_TIMEOUT)

                    s.connect((host, port))
                    logger.debug(f"Connected to {host}:{port}")

                    data = b""
                    while True:
                        new_data = s.recv(1024)
                        if not new_data:
                            break
                        data += new_data
                    logger.debug(f"Got {len(data)} bytes from connection")
                except (TimeoutError, OSError):  # noqa: B014
                    # TimeoutError is a subclass of OSError, but I leave it here
                    # for readability
                    attempts -= 1
                    logger.info(f"Did not get any new messages, retrying ({attempts=})")
                    time.sleep(1)
                    continue

                if not data:
                    attempts -= 1
                    logger.info(f"Did not get any new messages, retrying ({attempts=})")
                    time.sleep(1)
                    continue

                # Assume utf-8 encoding and JSON, attempt to convert to message
                try:
                    result.append(DeadDropMessage.model_validate_json(data))
                except ValidationError as e:
                    logger.error(
                        f"Failed to convert {repr(data)} to a DeadDropMessage, ignoring message: {e}"
                    )

        # Arbitrary response
        return result

    @classmethod
    def recv_msg_by_listening(cls, args: dict[str, Any]) -> list[DeadDropMessage]:
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

        host = local_cfg.PLAINTEXT_TCP_LISTEN_BIND_HOST
        port = local_cfg.PLAINTEXT_TCP_LISTEN_RECV_PORT

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            start_time = time.time()

            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # This sets an absolute limit on blocking operations, but is not
            # the primary form of guaranteeing this operates for a short period
            # of time
            s.settimeout(local_cfg.PLAINTEXT_TCP_LISTEN_TIMEOUT)
            logger.debug(f"Binding to {host}:{port} to receive new messages")

            # Wait until we get the listener. In an ideal world, this reduces
            # the likelihood that all of the following happen:
            # - Docker is exposing the target port, so the connection from the
            #   sender goes through and it *thinks* the agent actually got the message
            # - but the port was just in use, and therefore a listener
            #   can't be set up
            # - and in the time between the old worker releasing the listener
            while True:
                try:
                    s.bind((host, port))
                    s.listen()
                    break
                except OSError as e:
                    # We only ever expect this to raise "address already in use"
                    if e.errno != errno.EADDRINUSE:
                        raise e
                    else:
                        # Keep trying to get the listener. From observation,
                        # the result is that this actually keeps "backing up"
                        # indefinitely (until the soft time limit is reached),
                        # but the net result is that *some* listener is always
                        # up, and therefore we don't get dropped messages
                        #
                        # Note that this is not a solution to the "competing
                        # listeners" problem; if you try to run two mini_server.py
                        # instances at once, one will eat both responses and the
                        # other will never get its response. This is a non-issue
                        # in practice, since there should only ever be one server.
                        time.sleep(0.5)

            while True:
                # Accept connections
                try:
                    # This can take up to the duration set by `s.settimeout`;
                    # if nothing is received during that time, assume there
                    # are no new messages to receive
                    logger.debug(f"Checking for connection over {host}:{port}")
                    client, addr = s.accept()
                    logger.debug(f"Got connection from {addr}")
                except TimeoutError:
                    break

                # Get all data
                data = b""
                while True:
                    new_data = client.recv(1024)
                    if not new_data:
                        break
                    data += new_data
                logger.debug(f"Got {len(data)} bytes from connection")

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
