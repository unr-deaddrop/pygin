"""
Shared library for all protocol-related objects for Pygin.
"""

from base64 import b64decode, b64encode
from datetime import datetime
from typing import ClassVar
import binascii

from pydantic import field_serializer, field_validator
import redis

from src.libs.protocol_lib import DeadDropMessage


class PyginMessage(DeadDropMessage):
    """
    Extension of the DeadDrop message format with additional overhead, used
    in supporting Pygin-specific architecture.

    It should be equivalent to `AgentMessage` in purpose and implementation
    when compared to the prototype agent.
    """

    # The prefix used when using this class to directly add itself to a Redis
    # instance. Guarantees all keys with this prefix are representative of a
    # particular message.
    REDIS_KEY_PREFIX: ClassVar[str] = "agent-msg-parsed-"

    @field_validator("data", mode="before")
    @classmethod
    def validate_data(cls, v: str | bytes):
        """
        Before validation, assume that incoming string data is base64-encoded;
        decode it if so.

        If the incoming data is `bytes`, keep it exactly as is.
        """
        if isinstance(v, str):
            try:
                v = b64decode(v, validate=True)
            except binascii.Error:
                pass

        return v

    @field_serializer("data", when_used="json-unless-none")
    def serialize_data(self, data: bytes, _info):
        """
        On JSON serialization, the data field is always a base64-encoded message.
        In all other cases, it is kept as `bytes`.
        """
        return b64encode(data).decode()

    @field_serializer("timestamp", when_used="json-unless-none")
    def serialize_timestamp(self, timestamp: datetime, _info):
        """
        On JSON serialization, the timestamp is always numeric.
        """
        return timestamp.timestamp()

    def get_redis_key(self) -> str:
        """
        Retrive this message's resulting Redis key.
        """
        return self.REDIS_KEY_PREFIX + str(self.message_id)

    def insert_to_redis(self, redis_con: redis.Redis) -> str:
        """
        Insert this message as a dictionary into a Redis database.

        The key used is "agent-msg-parsed-{uuid}". Returns the Redis key used.
        """
        key = self.get_redis_key()
        # redis_con.hset(key, mapping=self.model_dump())
        redis_con.set(key, self.model_dump_json())
        return key

    def verify_message(self, key: str) -> bool:
        raise NotImplementedError

    def sign_message(self, key: str) -> bool:
        raise NotImplementedError
