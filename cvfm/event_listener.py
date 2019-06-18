import logging

from cvfm.constants import EVENTS_TO_OBSERVE, WAIT_FOR_UPDATE_TIMEOUT

logger = logging.getLogger(__name__)


class EventListener(object):
    def __init__(
        self, controller, update_set_queue, vcenter_api_client, database
    ):
        self._controller = controller
        self._vcenter_api_client = vcenter_api_client
        self._database = database
        self._update_set_queue = update_set_queue

    def listen(self, to_supervisor):
        logger.info("Event listener greenlet start working")
        event_history_collector = self._vcenter_api_client.create_event_history_collector(
            EVENTS_TO_OBSERVE
        )
        self._vcenter_api_client.add_filter(
            event_history_collector, ["latestPage"]
        )
        self._vcenter_api_client.make_wait_options(WAIT_FOR_UPDATE_TIMEOUT)
        self._safe_wait_for_update(to_supervisor)
        self._sync()
        while True:
            update_set = self._safe_wait_for_update(to_supervisor)
            if update_set:
                self._update_set_queue.put(update_set)

    def _sync(self):
        self._controller.sync()

    def _safe_wait_for_update(self, to_supervisor):
        to_supervisor.put("START_WAIT_FOR_UPDATES")
        update_set = self._vcenter_api_client.wait_for_updates()
        to_supervisor.put("AFTER_WAIT_FOR_UPDATES")
        return update_set
