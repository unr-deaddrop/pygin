"""
Base definitions for protocols and the DeadDrop standard message format.

TODO: In the distant future, this should be its own library. It is being included
with the Pygin distribution since we currently don't *have* another agent type.
Important to note is that this being its own library doesn't need to happen
for the server to work, since everything should be exported as a JSON by any
agent anyways.

This library must not import any other internal libraries; it may only import
the standard library and external packages.

Each protocol is implemented as a subclass of ProtocolBase, an abstract class
containing several properties that may (or may not) be defined.

The available protocols for a particular agent are determined by inspecting all
available subclasses of ProtocolBase.

When a protocol depends on some external library or binary, it is assumed to be
managed *outside* of the Python environment; that is, it does not need to be
installed as part of the normal Python environment setup process, and can be
handled by an initial setup script at the OS level.
"""

from base64 import b64encode, b64decode
from datetime import datetime
from enum import Enum
from textwrap import dedent
from typing import Any, Type
import abc
import configparser
import uuid
import json

from pydantic import BaseModel, Field, field_serializer, field_validator

from src.libs.argument_lib import ArgumentParser


class DeadDropMessageType(str, Enum):
    """
    String enumeration of all available message types.
    """

    # Message generated in response to a command. Messages of this type are only
    # ever generated by agents.
    CMD_RESPONSE = "command_response"

    # Message generated as a request for an agent to execute a command. Messages
    # of this type are only ever generated by agents.
    CMD_REQUEST = "command_request"

    # One or more log entries generated by an agent. One "log message" may contain
    # multiple log entries, as the "payload" field may
    LOG_MESSAGE = "log_message"

    # Heartbeat message generated by an agent. May contain additional diagnostic
    # data.
    HEARTBEAT = "heartbeat"

    # Heartbeat
    INIT_MESSAGE = "init_message"


class DeadDropMessage(BaseModel, abc.ABC):
    """
    Class representing the basic definition of a DeadDrop message.

    All messages contain the following information:
    - One of five standard message types (dictated by DeadDropMessageType).
    - The server-side user ID associated with the message, if any, for
      accountability purposes.
    - The ID of the agent where the message originated from. If the message
      is forwarded, this contains the ID of the original agent that constructed
      this message. If the message originates from the server, this is empty.
    - The ID of the message, a UUID.
    - The timestamp of the message.
    - The digest of the message, intended to be a digital signature. The agent
      stores its own private key and the public key of the server; the server
      stores its own private key and the public key of the agent. It is important
      to note that the agent's private key is not protected from discovery; it is
      therefore possible to forge valid messages originating from a particular agent.
      This weakness is outside the intended scope of this project.
    - A "payload" field, which contains the actual payload of the message. The
      payload is another JSON dictionary that varies in sturcture depending on
      the message type. Generally, the payload is considered

    Note that the encryption or fragmentation of messages is delegated to protocols.
    It is best to think of the standard messaging system as the application layer,
    and the covert communication protocols as the transport layer.

    In the future, these messages may be wrapped in another JSON object containing
    forwarding information, effectively allowing it to be routed (as if it were
    at the networking layer). This is not planned in the short term.
    """

    # The underlying message type.
    message_type: DeadDropMessageType

    # The UUID of the message. If not set at construct time, it is set
    # to a random value (i.e. uuidv4).
    message_id: uuid.UUID = Field(default_factory=uuid.uuid4)

    # The user this message is associated with. May be null if not associated
    # with a user.
    user_id: uuid.UUID = Field(default_factory=lambda: uuid.UUID(int=0))

    # The agent ID, or null if sent by the server.
    source_id: uuid.UUID = Field(default_factory=lambda: uuid.UUID(int=0))

    # The timestamp that this message was created. Assume UTC.
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Underlying message data. It is up to the code constructing messages to
    # ensure that the subfields of `payload` are JSON serializable. In most cases,
    # there is no well-defined structure for the inner fields of `payload`,
    # though certain immediate children may be required.
    #
    # TODO: How do we enforce that? If payload has a fixed structure based on
    # message_type, shouldn't that be its own submodel?
    payload: dict[str, Any] | None = None

    # Digital signature, if set.
    digest: bytes | None = None

    @field_serializer("timestamp", when_used="json-unless-none")
    @classmethod
    def serialize_timestamp(cls, timestamp: datetime, _info):
        """
        On JSON serialization, the timestamp is always numeric.
        """
        return timestamp.timestamp()

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v: Any) -> datetime:
        """
        Convert a timestamp back to a native Python datetime object.
        """
        if type(v) is datetime:
            return v

        if type(v) is str:
            try:
                return datetime.utcfromtimestamp(float(v))
            except Exception as e:
                raise ValueError(
                    f"Assumed string timestamp conversion of {v} failed."
                ) from e

        if type(v) is float:
            try:
                return datetime.utcfromtimestamp(v)
            except Exception as e:
                raise ValueError(
                    f"Attempted timestamp conversion of {v} failed."
                ) from e

        raise ValueError("Unexpected type for timestamp")

    @field_serializer("digest", when_used="json-unless-none")
    @classmethod
    def serialize_digest(cls, digest: bytes, _info):
        """
        On JSON serialization, the digest is base64.
        """
        return b64encode(digest).decode("utf-8")

    @field_validator("digest", mode="before")
    @classmethod
    def validate_digest(cls, v: Any) -> bytes | None:
        """
        On validation, the digest should be bytes. If it's a string,
        assume it's base64.
        """
        if v is None:
            return None

        if type(v) is str:
            return b64decode(v)

        if type(v) is bytes:
            return v

        raise ValueError("Unexpected type for digest")


class ProtocolConfig(BaseModel, abc.ABC):
    @property
    @abc.abstractmethod
    def section_name(self) -> str:
        """
        The configuration "section" used in configuration files.

        This MUST be the same as the module name.
        """
        pass

    @property
    @abc.abstractmethod
    def dir_attrs(self) -> list[str]:
        """
        A list of attributes that represent directories that need to be created
        at runtime.
        """
        pass

    @property
    @abc.abstractmethod
    def checkin_interval_name(self) -> str:
        """
        The config key/attribute that contains the checkin interval for this
        protocol.
        """
        pass

    def get_checkin_interval(self) -> int:
        """
        The checkin interval for this protocol.
        """
        return getattr(self, self.checkin_interval_name)

    def create_dirs(self) -> None:
        """
        Create any associated directories.
        """
        for field in self.dir_attrs:
            getattr(self, field).resolve().mkdir(exist_ok=True, parents=True)

    @classmethod
    def from_cfg_parser(cls, cfg_parser: configparser.ConfigParser) -> "ProtocolConfig":
        # Property, always returning string.
        try:
            cfg_obj = cls.model_validate(cfg_parser[cls.section_name])  # type: ignore[index]
        except KeyError as e:
            raise RuntimeError(
                f"Missing configuration section for protocol {cls.section_name}, is it defined?"
            ) from e
        cfg_obj.create_dirs()
        return cfg_obj


class ProtocolArgumentParser(ArgumentParser, abc.ABC):
    @classmethod
    def from_config_obj(cls, config: ProtocolConfig) -> "ProtocolArgumentParser":
        """
        Generate an argument parser from a ProtocolConfig object, setting
        the values from the ProtocolConfig object.
        """
        arg_obj = cls()
        if not arg_obj.parse_arguments(config.model_dump()):
            raise ValueError(f"{config} did not fill the required arguments for {cls}")

        return arg_obj


class ProtocolBase(abc.ABC):
    """
    Abstract base class representing the standard definition of a protocol
    for Python-based agents.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        The internal protocol name displayed to users and used in internal
        messaging.

        It is preferred that this is a valid Python variable name for future
        compatibility.
        """
        pass

    @property
    @abc.abstractmethod
    def version(self) -> str:
        """
        The version string for this protocol implementation.
        """
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """
        A brief description of this protocol, to be displayed to users (primarily)
        through the web interface.
        """
        pass

    @property
    @abc.abstractmethod
    def config_parser(self) -> Type[ArgumentParser]:
        """
        The configuration (argument) parser for this protocol.

        ---

        The reasoning for reusing ArgumentParser:

        At the end of the day, we could implement configuration for each protocol
        as a Pydantic model, a dataclass, and a bunch of other things that make
        sense. But ArgumentParser gives us exactly what we want: a way to expose
        configurable options for a particular protocol in a platform-independent
        manner, while still allowing us to use a dictionary of arguments if we
        really want to.

        At the same time, though, we'd still like to leverage Pydantic models for
        configuration, just as we are for the control unit. This is a decent
        compromise between the two,

        I don't really think this is the right way to do this, but let's just try
        it for now and see how it goes. There's plenty of arguments to be made,
        and I don't really know what's the best way to do this.

        ```py
        @abc.abstractmethod
        def send_msg(cls, msg, **kwargs) -> bytes:
            pass

        def send_msg(cls, msg, arg_1, arg_2, arg_3) -> bytes:
            pass
        ```

        but that violates LSP.
        """
        pass

    @classmethod
    @abc.abstractmethod
    def send_msg(cls, msg: DeadDropMessage, args: dict[str, Any]) -> dict[str, Any]:
        """
        Send an arbitrary binary message.

        This function should implement any mechanisms needed to split messages,
        place messages at an agreed-upon location, and so on. If any additional
        paramters are required for this to function, such as the credentials
        needed to access the account used for transferring information, they
        may be passed as protocol-specific keyword arguments.

        This function may raise exceptions.

        The return value of this function is always a dict, but the underlying
        structure may be anything; it is up to the agent core to decide how to
        handle the responses of a particular protocol implementation.

        :param msg: The binary message to send.
        """
        pass

    @classmethod
    @abc.abstractmethod
    def get_new_messages(cls, args: dict[str, Any]) -> list[DeadDropMessage]:
        """
        Retrieve all new messages that have yet to be retrieved.

        This function should make a best-effort attempt at ensuring that messages
        that have already been retrieved in the past are not retrieved again.
        However, it is up to the server or agent to ensure that it is not
        acting on duplicated messages, since a message may have been sent over
        more than one protocol.

        Diagnostic data as a result of retrieving the messages should be logged;
        it is not returned as part of the return value.

        If additional arguments are required for this to operate, such as the
        credentials needed to log onto an account or a shared meeting, they
        may be passed as either a configuration object or keyword arguments.

        This function may raise exceptions, such as if a service is inaccessible.
        """
        pass

    def to_dict(self) -> dict[str, Any]:
        """
        Return this protocol's metadata as a dictionary.

        Note that for compatibility purposes, ensure that the resulting dictionary
        is completely JSON serializable.
        """
        return {
            "name": self.name,
            "description": dedent(self.description).strip(),
            "version": self.version,
            "arguments": self.config_parser().model_dump()["arguments"],
        }


def export_all_protocols() -> list[Type[ProtocolBase]]:
    """
    Return a list of visible protocol classes.

    The protocol lookup occurs by inspecting all available subclasses of ProtocolBase
    when this function is executed.

    Note that "visible" means that the associated subclasses of ProtocolBase must
    already have been imported. If you implement a script to generate the command JSONs,
    you will need to import the commands ahead of time.
    """
    return ProtocolBase.__subclasses__()


def export_all_protocol_configs() -> list[Type[ProtocolConfig]]:
    """
    Return a list of visible protocol configuration objects.

    Refer to export_all_protocols() above.
    """
    return ProtocolConfig.__subclasses__()


def get_protocols_as_dict() -> dict[str, Type[ProtocolBase]]:
    """
    Return a dictionary of commands, suitable for lookup.

    The keys are the `name` attribute of each command found; the values are the
    literal types for each command (a subclass of CommandBase).
    """
    # mypy doesn't handle properties well; this works in practice, and the type
    # of cmd.name is *always* str
    return {proto.name: proto for proto in export_all_protocols()}  # type: ignore[misc]


def lookup_protocol(protocol_name: str) -> Type[ProtocolBase]:
    """
    Search for a provided protocol.
    """
    try:
        return get_protocols_as_dict()[protocol_name]
    except KeyError:
        raise RuntimeError(
            f"Failed to find protocol {protocol_name}, either it doesn't exist or it isn't visible"
        )


def export_protocols_as_json(protocol_classes: list[Type[ProtocolBase]], **kwargs):
    """
    Return a nicely formatted string containing all command information,
    suitable for presentation in the DeadDrop interface.
    """
    json_objs: list[dict[str, Any]] = []
    for command_class in protocol_classes:
        json_objs.append(command_class().to_dict())

    return json.dumps(json_objs, **kwargs)
