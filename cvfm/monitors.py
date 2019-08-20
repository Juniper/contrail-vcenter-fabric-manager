import logging

import gevent
from gevent import hub, queue

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
        self._message_q = queue.Queue()

    def start(self):
        self._vnc_rabbit_client.callback = self.callback
        while True:
            # try:
            self._message_q.get()
            logger.info("Topology change detected - Synchronization required.")
            # self._wait_before_sync()
            self._controller.sync()
            # except gevent.queue.Empty:
            #     gevent.sleep(0)

    def callback(self, msg_body):
        if not self._topology_changed(msg_body):
            return
        self._message_q.put(msg_body, block=False)

    def _wait_before_sync(self):
        try:
            self._message_q.get(timeout=5)
        except gevent.queue.Empty:
            gevent.sleep(1)

    @staticmethod
    def _topology_changed(msg_body):
        return msg_body.get("type") in const.VNC_TOPOLOGY_OBJECTS
