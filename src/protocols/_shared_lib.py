"""
Shared library for all protocol-related objects for Pygin.
"""

from typing import ClassVar

import redis

from src.libs.protocol_lib import DeadDropMessage


class PyginMessage(DeadDropMessage):
    """
    Extension of the DeadDrop message format with additional overhead, used
    in supporting Pygin-specific architecture.

    It should be equivalent to `AgentMessage` in purpose and implementation
    when compared to the prototype agent.

    NOTE: Right now, PyginMessage is generally unused since we moved away from
    using the JSON serializers for Celery. That's no longer the case, and we
    don't really need more than what DeadDropMessage provides, so this remains
    as unused legacy code.
    """

    # The prefix used when using this class to directly add itself to a Redis
    # instance. Guarantees all keys with this prefix are representative of a
    # particular message.
    #
    # The default is "agent-msg-parsed-", but may be changed at runtime. The intent
    # is that this should be changed by the Celery tasking module if needed.
    REDIS_KEY_PREFIX: ClassVar[str] = "agent-msg-parsed-"

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
