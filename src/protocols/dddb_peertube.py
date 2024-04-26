"""
The PeerTube messaging protocol.
"""

from dataclasses import dataclass
from typing import Type, Any, ClassVar
import logging

from pydantic import Field

from dddb.video.peertube import dddbPeerTube
from dddb.video import dddbDecodeVideo, dddbEncodeVideo

from deaddrop_meta.protocol_lib import (
    ProtocolBase,
    ProtocolConfig,
    DeadDropMessage,
)
from deaddrop_meta.interface_lib import EndpointMessagingData

logger = logging.getLogger(__name__)


class dddbPeerTubeConfig(ProtocolConfig):
    """
    Model detailing available configuration options for dddb_peertube.
    """

    DDDB_PEERTUBE_CHECKIN_FREQUENCY: int = Field(
        default=20,
        json_schema_extra={
            "description": "The frequency with which to check for messages via PeerTube."
        },
    )
    DDDB_PEERTUBE_EMAIL: str = Field(
        default="",
        json_schema_extra={"description": "The target PeerTube username."},
    )
    DDDB_PEERTUBE_PASSWORD: str = Field(
        default="",
        json_schema_extra={"description": "The target PeerTube password."},
    )
    DDDB_PEERTUBE_HOST: str = Field(
        default="http://peertube.localhost:9000",
        json_schema_extra={"description": "The full URL to the root of the PeerTube instance."},
    )

    checkin_interval_name: ClassVar[str] = "DDDB_PEERTUBE_CHECKIN_FREQUENCY"
    section_name: ClassVar[str] = "dddb_peertube"
    dir_attrs: ClassVar[list[str]] = []  # No directories needed

    def convert_to_server_config(
        self, endpoint: EndpointMessagingData
    ) -> "dddbPeerTubeConfig":
        # Make deep copy of current config
        new_cfg = self.model_copy(deep=True)

        # Literally nothing needs to be changed
        return new_cfg


class dddbPeerTubeProtocol(ProtocolBase):
    """
    Implements the PeerTube-based video protocol for Pygin.
    """

    name: str = "dddb_peertube"
    description: str = __doc__
    version: str = "0.0.1"
    config_model: Type[ProtocolConfig] = dddbPeerTubeConfig
    supports_bytes: bool = False

    @classmethod
    def send_msg(cls, msg: DeadDropMessage, args: dict[str, Any]) -> dict[str, Any]:
        local_cfg: dddbPeerTubeConfig = dddbPeerTubeConfig.model_validate(args)

        peertube_obj = dddbPeerTube(local_cfg.DDDB_PEERTUBE_HOST, local_cfg.DDDB_PEERTUBE_EMAIL, local_cfg.DDDB_PEERTUBE_PASSWORD)
        if not peertube_obj.is_authenticated():
            raise RuntimeError("Failed to log into PeerTube instance")
        
        raw_data = msg.model_dump_json().encode("utf-8")
        encode_video_obj = dddbEncodeVideo(raw_data)
        res = peertube_obj.post(encode_video_obj.getBytes(), dest="test2", src="test1")
        
        if not res:
            raise RuntimeError("Posting to PeerTube failed!")
        
        # No data to return
        return {}

    @classmethod
    def get_new_messages(cls, args: dict[str, Any]) -> list[DeadDropMessage]:
        local_cfg: dddbPeerTubeConfig = dddbPeerTubeConfig.model_validate(args)

        peertube_obj = dddbPeerTube(local_cfg.DDDB_PEERTUBE_HOST, local_cfg.DDDB_PEERTUBE_EMAIL, local_cfg.DDDB_PEERTUBE_PASSWORD)
        if not peertube_obj.is_authenticated():
            raise RuntimeError("Failed to log into PeerTube instance")
        
        response = peertube_obj.get(dest="test2")
        decode_video_obj = dddbDecodeVideo(response[0]['data'])
        
        # right now this only returns one message
        msg = DeadDropMessage.model_validate_json(decode_video_obj.getBytes())
        return [msg]
        
        
        

        