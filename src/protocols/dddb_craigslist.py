"""
Plaintext TCP-based implementation of the dddb messaging protocol.

Used for debugging, doesn't have any dependencies.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Type, Any, ClassVar, Union
import logging
import os
import pickle
import sys
import time

from pydantic import Field

from dddb.text.craigslist import dddbCraigslist

from deaddrop_meta.protocol_lib import (
    ProtocolBase,
    ProtocolConfig,
    DeadDropMessage,
)
from deaddrop_meta.interface_lib import EndpointMessagingData

from selenium.webdriver import FirefoxOptions
import redis
import pottery

logger = logging.getLogger(__name__)

REDIS_HOST = "127.0.0.1"
if sys.platform != "win32" and os.getenv("IS_DOCKER") == True:
    REDIS_HOST = "redis"
    logger.info(f"Docker flag set, pointing Redis at container name")
logger.info(f"Assuming Redis is available at {REDIS_HOST=}")

# The key used to store the last read time, as well as the cookies set in the
# driver.
CRAIGSLIST_INSTANCE_KEY: str = "_dddb_craigslist-instance"
# The key used for the instance lock.
CRAIGSLIST_INSTANCE_LOCK: str = "_dddb_craigslist-lock"
# The timeout on the lock before it is auto-released. In general, this should be
# greater than or equal to the task auto-timeout. That said, the context manager
# should automatically take the lock down where applicable.
CRAIGSLIST_LOCK_TIMEOUT: int = 300


class dddbCraigslistConfig(ProtocolConfig):
    """
    Model detailing available configuration options for dddb_craigslist.
    """

    DDDB_CRAIGSLIST_CHECKIN_FREQUENCY: int = Field(
        default=30,
        json_schema_extra={
            "description": "The frequency with which to check for messages via Craigslist."
        },
    )
    DDDB_CRAIGSLIST_EMAIL: str = Field(
        json_schema_extra={"description": "The Craigslist email."},
    )
    DDDB_CRAIGSLIST_PASSWORD: str = Field(
        json_schema_extra={"description": "The Craigslist password."},
    )
    DDDB_CRAIGSLIST_LOCKFILE: Path = Field(
        json_schema_extra={
            "description": "If present, stall on sends and receives until inaccessible."
        },
    )
    DDDB_CRAIGSLIST_HEADLESS: bool = Field(
        json_schema_extra={"description": "Whether to use --headless for Firefox."},
    )

    checkin_interval_name: ClassVar[str] = "DDDB_CRAIGSLIST_CHECKIN_FREQUENCY"
    section_name: ClassVar[str] = "dddb_craigslist"
    dir_attrs: ClassVar[list[str]] = []  # No directories needed

    def convert_to_server_config(
        self, endpoint: EndpointMessagingData
    ) -> "dddbCraigslistConfig":
        # Make deep copy of current config
        new_cfg = self.model_copy(deep=True)

        # Literally nothing needs to be changed
        return new_cfg


@dataclass
class CraigslistInstanceData:
    """
    Contains the information needed to reconstruct a full dddbCraigslist
    instance without needing to re-invoke logins or pickle the entire
    object (which is impossible).
    """

    cookies: list[dict[str, Any]]

    email: str
    password: str
    last_time: float

    @staticmethod
    def from_pickle(data: bytes, local_cfg: dddbCraigslistConfig) -> dddbCraigslist:
        """
        Reconstruct and reinitialize a dddbCraigslist instance from raw bytes.
        """
        instance_data: "CraigslistInstanceData" = pickle.loads(data)

        opts = FirefoxOptions()
        if local_cfg.DDDB_CRAIGSLIST_HEADLESS:
            opts.add_argument("--headless")

        cl_obj = dddbCraigslist(
            email=instance_data.email, password=instance_data.password, options=opts
        )

        # Manually override any other values - this has the function equivalence
        # of a cl_obj.login() call, as well as advancing the state to the most
        # recent cl_obj.get() call
        cl_obj.last_time = instance_data.last_time

        # Manually set cookies
        cl_obj.driver.get("https://reno.craigslist.org")
        for cookie in instance_data.cookies:
            cl_obj.driver.add_cookie(cookie)

        return cl_obj

    @classmethod
    def to_pickle(cls, cl_obj: dddbCraigslist) -> bytes:
        """
        Convert a dddbCraigslist instance to a pickleable object.
        """
        instance_obj = cls(
            cookies=cl_obj.driver.get_cookies(),
            email=cl_obj.email,
            password=cl_obj.password,
            last_time=cl_obj.last_time,
        )

        return pickle.dumps(instance_obj)


class dddbCraigslistProtocol(ProtocolBase):
    """
    Implements the Craigslist protocol for Pygin.

    When a Redis instance is available, this attempts to retrieve a pickled
    dddbCraigslist object.

    While pickling is obviously unsafe, it is reasonable to assume that somebody
    with the power to write unsafed pickled objects to the Redis database (most
    likely, having access to the machine themselves) could perform destructive
    actions to begin with, with or without the help of the agent. The risk here
    is that a message could be sent on behalf of the agent (already possible through
    other means), or that the agent could be used to run arbitrary code (again,
    already possible through simpler means).

    Unless the Redis database were exposed to the world - which it shouldn't be -
    I think the risk of this operation is outside of our scope.
    """

    name: str = "dddb_craigslist"
    description: str = __doc__
    version: str = "0.0.1"
    config_model: Type[ProtocolConfig] = dddbCraigslistConfig

    @classmethod
    def send_msg(cls, msg: DeadDropMessage, args: dict[str, Any]) -> dict[str, Any]:
        local_cfg: dddbCraigslistConfig = dddbCraigslistConfig.model_validate(args)

        # Soft warnings
        if not local_cfg.DDDB_CRAIGSLIST_HEADLESS and sys.platform != "win32":
            logger.warning(
                "Non-Windows environment detected. Selenium has not been"
                " configured to run headless, which will cause it to fail in a"
                " container!"
            )

        # Demo code/throttling
        lockfile = local_cfg.DDDB_CRAIGSLIST_LOCKFILE.resolve()
        while True:
            if not lockfile.exists():
                break
            logger.info(f"Lockfile {lockfile} present, waiting before sending")
            time.sleep(2)

        redis_con = None
        # Using the context manager in a best effort to guarantee release.
        try:
            redis_con = redis.Redis(host=REDIS_HOST, port=6379)
            redis_con.ping()
            logger.info("Redis connection available, using lock and trying unpickle")
        except redis.ConnectionError:
            redis_con = None
            logger.info("No redis connection available, lock will not be used")

        # If Redis is available, use a lock and use that instance
        if redis_con:
            logger.debug("Attempting to acquire lock (post)")
            with pottery.Redlock(
                key=CRAIGSLIST_INSTANCE_LOCK, masters={redis_con}, auto_release_time=300
            ):
                logger.debug("Got lock (post)")
                cl_obj = cls.get_stored_instance(local_cfg)
                result = cls.perform_post(cl_obj, msg)
                cls.save_instance(cl_obj)
                return result

        # Otherwise, just operate normally
        cl_obj = cls.get_stored_instance(local_cfg)
        return cls.perform_post(cl_obj, msg)

    @classmethod
    def get_new_messages(cls, args: dict[str, Any]) -> list[DeadDropMessage]:
        local_cfg: dddbCraigslistConfig = dddbCraigslistConfig.model_validate(args)

        # Soft warnings
        if not local_cfg.DDDB_CRAIGSLIST_HEADLESS and sys.platform != "win32":
            logger.warning(
                "Non-Windows environment detected. Selenium has not been"
                " configured to run headless, which will cause it to fail in a"
                " container!"
            )

        # Demo code/throttling
        lockfile = local_cfg.DDDB_CRAIGSLIST_LOCKFILE.resolve()
        while True:
            if not lockfile.exists():
                break
            logger.info(f"Lockfile {lockfile} present, waiting before sending")
            time.sleep(2)

        # Using the context manager in a best effort to guarantee release.
        redis_con = None
        try:
            redis_con = redis.Redis(host=REDIS_HOST, port=6379)
            redis_con.ping()
            logger.info("Redis connection available, using lock and trying unpickle")
        except redis.ConnectionError:
            redis_con = None
            logger.info("No redis connection available, lock will not be used")

        # If Redis is available, use a lock and use that instance
        if redis_con:
            logger.debug("Attempting to acquire lock (get)")
            with pottery.Redlock(
                key=CRAIGSLIST_INSTANCE_LOCK, masters={redis_con}, auto_release_time=300
            ):
                logger.debug("Got lock (get)")
                cl_obj = cls.get_stored_instance(local_cfg)
                result = cls.perform_get(cl_obj)
                cls.save_instance(cl_obj)
                return result

        # Otherwise, just operate normally
        cl_obj = cls.get_stored_instance(local_cfg)
        return cls.perform_get(cl_obj)

    @staticmethod
    def perform_get(cl_obj: dddbCraigslist) -> list[DeadDropMessage]:
        # It's assumed a login has already been performed
        raw_msgs = cl_obj.get()

        res = []
        for raw_msg in raw_msgs:
            try:
                msg = DeadDropMessage.model_validate_json(raw_msg)
                res.append(msg)
            except Exception:
                # Could be a fragment of an older message or something completely
                # random, fine to ignore.
                logger.error(f"Failed to decode data to DeadDropMessage: {raw_msg}")
                continue

        return res

    @staticmethod
    def perform_post(cl_obj: dddbCraigslist, msg: DeadDropMessage) -> dict[str, Any]:
        # It's assumed a login has already been performed
        data = msg.model_dump_json().encode("utf-8")
        cl_obj.post(data)

        return {}

    @staticmethod
    def get_stored_instance(
        local_cfg: dddbCraigslistConfig,
    ) -> Union[dddbCraigslist, None]:
        """
        Attempt to deserialize a stored Craigslist instance from the database, or
        create (but do not save) a new instance.

        Note that it is impossible to pickle an entire instance directly. However,
        it *is* possible to save the cookies and the time that Craigslist was last
        queried according to the Craigslist instance. A full Craigslist instance
        can therefore be manually constructed by navigating to Craigslist (required
        for `addCookie()` to work), re-adding stored cookies (if any), and then
        re-setting the time. This effectively places the entire instance at the
        same position as an older instance, even though we can't pickle the entire
        object.

        The documentation below assumes that a full instance could be pickled. It
        cannot, but the majority of the logic and reasoning still holds.y

        When no Redis instance is available, this always generates and
        returns a new instance (unconditionally). When a Redis instance
        is available:
        - If no dddbCraigslist object is present at the expected key, then
          one is created and returned.
        - If one is present, it is *copied* out and deserialized.

        One of the problems we identified is that the volume of login operations
        proved to not only be a performance issue, but also a general issue
        in that Craigslist would eventually force a one-time login link. One
        way to solve this is to reuse the state across multiple workers.
        Simultaneously, restricting use of the driver to only one client at a
        time effectively serves as a form of throttling for this protocol
        as a whole, further reducing the likelihood of the agent being caught
        for spam (and preventing resource exhaustion).

        This has "soft" concurrency safety using the Redlock algorithm (yes,
        overkill) as implemented by Pottery. In short, if a Redis connection
        can be made, then it is assumed that one of the following three states
        is true:
        - A Selenium driver has *never* been instantiated
        - A Selenium driver has been instantiated and is in use
        - A Selenium driver has been instantiated and is not in use

        Case 1 transitions to case 2 after the Selenium driver is created.

        This function only attempts to retrieve a stored instance. It should
        be protected by a lock.
        """
        try:
            redis_con = redis.Redis(host=REDIS_HOST, port=6379)

            pickle_data = redis_con.get(CRAIGSLIST_INSTANCE_KEY)
            if pickle_data is not None:
                cl_obj: dddbCraigslist = CraigslistInstanceData.from_pickle(
                    pickle_data, local_cfg
                )
                logger.info("Pickled object found, returning")
                return cl_obj

            logger.info("No pickled object found, creating new object")
        except redis.ConnectionError:
            logger.info("Could not connect to Redis, creating new object")

        logger.debug("Constructing new object from provided arguments")

        # Initialize the object
        opts = FirefoxOptions()
        if local_cfg.DDDB_CRAIGSLIST_HEADLESS:
            opts.add_argument("--headless")

        new_obj = dddbCraigslist(
            email=local_cfg.DDDB_CRAIGSLIST_EMAIL,
            password=local_cfg.DDDB_CRAIGSLIST_PASSWORD,
            options=opts,
        )

        # Always log in for new instances
        logger.debug("Logging in")
        new_obj.login()
        return new_obj

    @staticmethod
    def save_instance(cl_obj: dddbCraigslist) -> None:
        """
        Pickle and save a dddbCraigslist instance to the Redis database.

        When no Redis database is available, this is a no-op.

        This should be protected by the same lock as get_stored_instance()
        (that is, a dddbCraigslist operation is atomic).
        """
        try:
            redis_con = redis.Redis(host=REDIS_HOST, port=6379)
        except redis.ConnectionError:
            logger.info("Could not connect to Redis, no instance saving performed")
            return

        logger.info(f"Pickling and saving {cl_obj} to {CRAIGSLIST_INSTANCE_KEY}")

        # Note that the key is set indefinitely. It is not "expired", i.e.
        # it is assumed that the session never expires. This is likely untrue
        # in practice over a long time, but I can't imagine a case where this
        # ever becomes necessary for our use.
        redis_con.set(CRAIGSLIST_INSTANCE_KEY, CraigslistInstanceData.to_pickle(cl_obj))
