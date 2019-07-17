import logging

import gevent

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
            timeout = gevent.Timeout(WAIT_FOR_UPDATE_TIMEOUT * 2)
            timeout.start()
            try:
                update_set = self._vcenter_api_client.wait_for_updates()
                timeout.cancel()
                if update_set:
                    self._controller.handle_update(update_set)
            except gevent.Timeout:
                logger.error(
                    "Waiting for vCenter updates timed out. Reconnecting..."
                )
                self._renew_vcenter_connection_retry()
                self._init()
                self._controller.sync()
            finally:
                timeout.cancel()

    def _init(self):
        event_history_collector = self._vcenter_api_client.create_event_history_collector(
            EVENTS_TO_OBSERVE
        )
        self._vcenter_api_client.add_filter(
            event_history_collector, ["latestPage"]
        )
        self._vcenter_api_client.make_wait_options(WAIT_FOR_UPDATE_TIMEOUT)
        self._vcenter_api_client.wait_for_updates()

    def _renew_vcenter_connection_retry(self):
        i = 1
        while True:
            try:
                self._vcenter_api_client.renew_connection()
                logger.info("Successfully reconnected to vCenter")
                break
            except Exception:
                logger.error("Error during renewing connection to vCenter")
                gevent.sleep(2 * i)
                logger.error("Retrying to renew connection to vCenter...")
            i += 1
