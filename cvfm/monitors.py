from builtins import object
import logging

import gevent
from gevent import queue

from cvfm import constants as const

logger = logging.getLogger(__name__)


class VMwareMonitor(object):
    def __init__(self, vmware_controller, vcenter_api_client):
        self._controller = vmware_controller
        self._vcenter_api_client = vcenter_api_client
        self._init()

    def start(self):
        self._controller.sync()
        while True:
            update_set = self._vcenter_api_client.wait_for_updates()
            if update_set:
                self._controller.handle_update(update_set)
            gevent.sleep()

    def _init(self):
        event_history_collector = self._vcenter_api_client.create_event_history_collector(
            const.EVENTS_TO_OBSERVE
        )
        self._vcenter_api_client.add_filter(
            event_history_collector, ["latestPage"]
        )
        self._vcenter_api_client.make_wait_options(
            const.WAIT_FOR_UPDATE_TIMEOUT
        )
        self._vcenter_api_client.wait_for_updates()


class VNCMonitor(object):
    def __init__(self, vmware_controller, vnc_rabbit_client):
        self._controller = vmware_controller
        self._vnc_rabbit_client = vnc_rabbit_client
        self._vnc_rabbit_client.callback = self.callback
        self._message_q = queue.Queue()

    def start(self):
        while True:
            self._message_q.get()
            logger.info("Topology change detected - Synchronization required.")
            self._wait_until_topology_update_complete()
            self._controller.sync()

    def callback(self, msg_body):
        if not self._topology_changed(msg_body):
            return
        self._message_q.put(msg_body, block=False)

    def _wait_until_topology_update_complete(self):
        while True:
            try:
                self._message_q.get(
                    timeout=const.TOPOLOGY_UPDATE_MESSAGE_TIMEOUT
                )
            except gevent.queue.Empty:
                break

    @staticmethod
    def _topology_changed(msg_body):
        return msg_body.get("type") in const.VNC_TOPOLOGY_OBJECTS
