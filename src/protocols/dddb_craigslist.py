"""
Plaintext TCP-based implementation of the dddb messaging protocol.

Used for debugging, doesn't have any dependencies.
"""

from pathlib import Path
from typing import Type, Any, ClassVar
import logging
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

logger = logging.getLogger(__name__)


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
        json_schema_extra={"description": "If present, stall on sends and receives until inaccessible."},
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


class dddbCraigslistProtocol(ProtocolBase):
    """
    Implements the Craigslist protocol for Pygin.

    Note that Craigslist does its own state management, but this cannot be
    preserved internally unless a Redis database is made available. This
    *attempts* to store the last time in a Redis database if available,
    but no guarantee is made.
    """

    name: str = "dddb_craigslist"
    description: str = __doc__
    version: str = "0.0.1"
    config_model: Type[ProtocolConfig] = dddbCraigslistConfig

    @classmethod
    def send_msg(cls, msg: DeadDropMessage, args: dict[str, Any]) -> dict[str, Any]:
        local_cfg: dddbCraigslistConfig = dddbCraigslistConfig.model_validate(args)

        # Demo code/throttling
        lockfile = local_cfg.DDDB_CRAIGSLIST_LOCKFILE.resolve()
        while True:
            if not lockfile.exists():
                break
            logger.info(f"Lockfile {lockfile} present, waiting before sending")
            time.sleep(2)

        opts = FirefoxOptions()
        if local_cfg.DDDB_CRAIGSLIST_HEADLESS:
            opts.add_argument("--headless")

        data = msg.model_dump_json().encode("utf-8")

        cl_obj = dddbCraigslist(
            email=local_cfg.DDDB_CRAIGSLIST_EMAIL,
            password=local_cfg.DDDB_CRAIGSLIST_PASSWORD,
            options=opts
        )
        cl_obj.login()
        cl_obj.post(data)
        cl_obj.close()

    @classmethod
    def get_new_messages(cls, args: dict[str, Any]) -> list[DeadDropMessage]:
        local_cfg: dddbCraigslistConfig = dddbCraigslistConfig.model_validate(args)

        # Demo code/throttling
        lockfile = local_cfg.DDDB_CRAIGSLIST_LOCKFILE.resolve()
        while True:
            if not lockfile.exists():
                break
            logger.info(f"Lockfile {lockfile} present, waiting before receiving")
            time.sleep(2)

        opts = FirefoxOptions()
        if local_cfg.DDDB_CRAIGSLIST_HEADLESS:
            opts.add_argument("--headless")

        cl_obj = dddbCraigslist(
            email=local_cfg.DDDB_CRAIGSLIST_EMAIL,
            password=local_cfg.DDDB_CRAIGSLIST_PASSWORD,
            options=opts
        )
        cl_obj.login()
        raw_msgs = cl_obj.get()
        cl_obj.close()

        res = []
        for raw_msg in raw_msgs:
            try:
                msg = DeadDropMessage.model_validate_json(raw_msg)
                res.append(msg)
            except Exception as e:
                # Could be a fragment of an older message, fine to ignore.
                logger.error(f"Failed to decode message to DeadDropMessage: {raw_msg}")
                continue

        return res
