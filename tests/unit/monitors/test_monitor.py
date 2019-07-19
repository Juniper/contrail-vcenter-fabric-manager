import mock
import pytest

from cvfm.constants import EVENTS_TO_OBSERVE, WAIT_FOR_UPDATE_TIMEOUT
from cvfm.monitors import VMwareMonitor


@pytest.fixture
def vmware_controller():
    return mock.Mock()


@pytest.fixture
def vcenter_api_client():
    return mock.Mock()


def test_init(vmware_controller, vcenter_api_client):
    event_history_collector = mock.Mock()
    vcenter_api_client.create_event_history_collector.return_value = (
        event_history_collector
    )

    VMwareMonitor(vmware_controller, vcenter_api_client)

    vcenter_api_client.create_event_history_collector.assert_called_once_with(
        EVENTS_TO_OBSERVE
    )
    vcenter_api_client.add_filter.assert_called_once_with(
        event_history_collector, ["latestPage"]
    )
    vcenter_api_client.make_wait_options.assert_called_once_with(
        WAIT_FOR_UPDATE_TIMEOUT
    )
    vcenter_api_client.wait_for_updates.assert_called_once()


def test_start(vmware_controller, vcenter_api_client):
    update_set = mock.Mock()
    vcenter_api_client.wait_for_updates.side_effect = [None, update_set]
    vmware_monitor = VMwareMonitor(vmware_controller, vcenter_api_client)

    try:
        vmware_monitor.start()
    except StopIteration:
        pass

    vmware_controller.handle_update.assert_called_once_with(update_set)
    vmware_controller.sync.assert_called_once()
