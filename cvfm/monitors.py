from builtins import object
import logging

from cvfm.constants import EVENTS_TO_OBSERVE, WAIT_FOR_UPDATE_TIMEOUT

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

    def _init(self):
        event_history_collector = self._vcenter_api_client.create_event_history_collector(
            EVENTS_TO_OBSERVE
        )
        self._vcenter_api_client.add_filter(
            event_history_collector, ["latestPage"]
        )
        self._vcenter_api_client.make_wait_options(WAIT_FOR_UPDATE_TIMEOUT)
        self._vcenter_api_client.wait_for_updates()
