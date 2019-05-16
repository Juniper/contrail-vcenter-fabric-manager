import gevent
import logging

from cvfm.constants import SUPERVISOR_TIMEOUT

logger = logging.getLogger(__name__)


class Supervisor(object):
    def __init__(self, event_listener, vcenter_api_client):
        self._event_listener = event_listener
        self._vcenter_api_client = vcenter_api_client
        self._to_supervisor = gevent.queue.Queue()
        self._greenlet = None

    def supervise(self):
        self._greenlet = gevent.spawn(
            self._event_listener.listen, self._to_supervisor
        )
        while True:
            try:
                self._to_supervisor.get()
                self._to_supervisor.get(timeout=SUPERVISOR_TIMEOUT)
            except Exception:
                logger.error(
                    "Events listener greenlets hanged on WaitForUpdatesEx call"
                )
                logger.error("Renewing connection to vCenter...")
                self._renew_vcenter_connection_retry()
                logger.error("Renewed connection to vCenter")
                logger.error("Respawing event listener greenlet")
                self._greenlet.kill(block=False)
                self._greenlet = gevent.spawn(
                    self._event_listener.listen, self._to_supervisor
                )
                logger.error("Respawned event listener greenlet")

    def _renew_vcenter_connection_retry(self):
        i = 1
        while True:
            try:
                self._vcenter_api_client.renew_connection()
                break
            except Exception:
                logger.error("Error during renewing connection to vCenter")
                gevent.sleep(2 * i)
                logger.error("Retrying to renew connection to vCenter...")
            i += 1
