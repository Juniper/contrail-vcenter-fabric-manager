import mock
import pytest

from cvfm.monitors import VNCMonitor


@pytest.fixture
def vmware_controller():
    return mock.Mock()


@pytest.fixture
def vnc_rabbit_client():
    return mock.Mock()


@pytest.fixture
def vnc_monitor(vmware_controller, vnc_rabbit_client):
    return VNCMonitor(vmware_controller, vnc_rabbit_client)


def test_start(vnc_monitor, vnc_rabbit_client):
    vnc_monitor.start()

    assert vnc_rabbit_client.callback == vnc_monitor.callback


@pytest.mark.parametrize(
    "msg_body,call_count",
    [
        ({"type": "node"}, 1),
        ({"type": "port"}, 1),
        ({"type": "physical-router"}, 1),
        ({"type": "physical-interface"}, 1),
        ({"type": "project"}, 0),
    ],
)
def test_callback(
    msg_body, call_count, vnc_monitor, vmware_controller, vnc_rabbit_client
):
    vnc_monitor.start()
    vnc_rabbit_client.callback(msg_body)

    assert vmware_controller.sync.call_count == call_count
