import mock
import pytest

from cvfm.clients.rabbit import VNCRabbitClient


@pytest.fixture
def vnc_kombu_client():
    return mock.Mock()


@pytest.fixture
def rabbit_cfg():
    return {
        "rabbit_hosts": "10.10.10.10",
        "rabbit_port": 5673,
        "rabbit_user": "guest",
        "rabbit_password": "guest",
        "rabbit_vhost": "",
        "rabbit_ha_mode": False,
        "q_name": "cvfm.localhost.local",
        "heartbeat_seconds": 0,
    }


def test_set_callback(rabbit_cfg):
    vnc_monitor = mock.Mock()

    with mock.patch("cvfm.clients.rabbit.VncKombuClient") as vnc_kombu_client:
        vnc_rabbit_client = VNCRabbitClient(rabbit_cfg)
        vnc_rabbit_client.callback = vnc_monitor.callback

    rabbit_cfg.update(
        {
            "logger": VNCRabbitClient.logger,
            "subscribe_cb": vnc_monitor.callback,
        }
    )
    vnc_kombu_client.assert_called_once_with(**rabbit_cfg)
