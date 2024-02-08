"""
Base definitions for protocols and the DeadDrop standard message format.

Each protocol is implemented as a subclass of ProtocolBase, an abstract class
containing several properties that may (or may not) be defined.

The available protocols for a particular agent are determined by inspecting all
available subclasses of ProtocolBase.

When a protocol depends on some external library or binary, it is assumed to be
managed *outside* of the Python environment; that is, it does not need to be
installed as part of the normal Python environment setup process, and can be
handled by an initial setup script at the OS level.
"""

from enum import Enum
from typing import Type
import abc

from pydantic import BaseModel

# TODO: Copy information over from the prototype agent, make a generic ABC of
# DeadDrop messages and then have AgentMessage inherit from that class - this
# separates the "DeadDrop message format" from "what this agent needs to tack
# onto messages for anything to function"


class DeadDropMessageType(str, Enum):
    """
    String enumeration of all available message types.

    FIXME: This belongs in an external lib, not Pygin.
    """

    # TODO: Import from the prototype agent.


class DeadDropMessage(BaseModel):
    """
    Class representing the basic definition of a DeadDrop message.

    FIXME: This belongs in an external lib, not Pygin.
    """

    pass


class PyginMessage(DeadDropMessage):
    """
    Extension of the DeadDrop message format with additional overhead, used
    in supporting Pygin-specific architecture.

    It should be equivalent to `AgentMessage` in purpose and implementation
    when compared to the prototype agent.
    """


class ProtocolBase(BaseModel, abc.ABC):
    """
    Abstract base class representing the standard definition of a protocol
    for Python-based agents.
    """

    @property
    @abc.abstractmethod
    def protocol_name(self) -> str:
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

    @abc.abstractmethod
    def send_msg(self, msg: bytes, **kwargs) -> bytes:
        """
        Send an arbitrary binary message.

        This function should implement any mechanisms needed to split messages,
        place messages at an agreed-upon location, and so on. If any additional
        paramters are required for this to function, such as the credentials
        needed to access the account used for transferring information, they
        may be passed as protocol-specific keyword arguments.

        This function may raise exceptions.

        The return value of this function is always bytes, but the underlying
        structure may be anything; it is up to the agent core to decide how to
        handle the responses of a particular protocol implementation.

        :param msg: The binary message to send.
        """
        # TODO: does this actually work with Celery tasking?
        pass

    @abc.abstractmethod
    def check_for_msg(self, **kwargs) -> bytes:
        """
        Retrieve the least recent message that has yet to be retrieved.

        Each time this message is called, either an empty bytestring is returned,
        or the next available message is retrieved. The process of reconstructing
        messages, if needed, is handled opaquely.

        If additional arguments are required for this to operate, such as the
        credentials needed to log onto an account or a shared meeting, they
        may be passed as keyword arguments.

        This function may raise exceptions, such as if a service is inaccessible.
        """
        # TODO: does this actually work with Celery tasking?
        pass


def export_all_protocols() -> dict[str, Type[ProtocolBase]]:
    """
    Return a dictionary of available protocols.

    The keys are the `protocol_name` attribute of each protocol found;
    the values are the literal class definitions for each protocol.

    The protocol lookup occurs by inspecting all available subclasses of
    ProtocolBase when this function is executed.
    """
    raise NotImplementedError


def get_protocol_by_name(protocol_name: str) -> Type[ProtocolBase]:
    """
    Search for a protocol by name.

    If not found, raises RuntimeError.
    """
    raise NotImplementedError


def export_protocols_as_json():
    """
    Return a nicely formatted string containing all command information,
    suitable for presentation in the DeadDrop interface.
    """
    pass
