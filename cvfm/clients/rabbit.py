from builtins import object
import logging

from cfgm_common.vnc_kombu import VncKombuClient

logger = logging.getLogger(__name__)


class VNCRabbitClient(object):
    def __init__(self, rabbit_cfg):
        self._rabbit_cfg = rabbit_cfg
        self._callback = None
        self._kombu = None

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, cb_func):
        self._callback = cb_func
        self._rabbit_cfg.update(
            {"subscribe_cb": self._callback, "logger": self.logger}
        )
        self._kombu = VncKombuClient(**self._rabbit_cfg)

    @staticmethod
    def logger(msg, level):
        logger.log(level, msg)
