import gevent.queue
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


def test_start(vnc_monitor, vnc_rabbit_client, vmware_controller):

    with mock.patch.object(vnc_monitor, "_message_q") as msg_q:
        vmware_controller.sync.side_effect = IndexError
        msg_q.get.side_effect = [None, gevent.queue.Empty]
        with pytest.raises(IndexError):
            vnc_monitor.start()

    assert msg_q.get.call_count == 2
    assert vmware_controller.sync.called_once()


@pytest.mark.parametrize(
    "msg_body,call_count",
    [
        ({"type": "node"}, 1),
        ({"type": "port"}, 1),
        ({"type": "physical_router"}, 1),
        ({"type": "physical_interface"}, 1),
        ({"type": "project"}, 0),
    ],
)
def test_callback(
    msg_body, call_count, vnc_monitor, vmware_controller, vnc_rabbit_client
):
    with mock.patch.object(vnc_monitor, "_message_q") as msg_q:
        vnc_rabbit_client.callback(msg_body)

    assert msg_q.put.call_count == call_count
