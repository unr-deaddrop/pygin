"""
dddb-specific routines for operating "locally".

This assumes that the server (or some other source of messages) has access
to the local folders that the agent reads message from and writes messaages to.
This is useful in single-device demonstrations of DeadDrop, as well as remote
demonstrations of DeadDrop that do not involve an actual remote service.
"""

from src.libs.protocol_lib import ProtocolBase


class dddbLocalProtocol(ProtocolBase):
    """
    Local implementation of the dddb protocol.

    This leverages the local filesystem to "send" and "receive" videos, such that
    the server and the agent have agreed on folders for incoming and outgoing
    messages in advance.

    While this does not use an external protocol as intended by the framework,
    this demonstrates a proof-of-concept that avoids depending on an external
    service outside of our control.
    """

    name: str = "dddb_local"
    description: str = __doc__
    version: str = "0.0.1"

    def send_msg(self, msg: bytes, **kwargs) -> bytes:
        raise NotImplementedError

    def check_for_msg(self, **kwargs) -> bytes:
        raise NotImplementedError
