import mock
import pytest

from cvfm import synchronizers


@pytest.fixture
def database():
    return mock.Mock()


@pytest.fixture
def vm_synchronizer():
    return mock.Mock()


@pytest.fixture
def dpg_synchronizer():
    return mock.Mock()


@pytest.fixture
def vpg_synchronizer():
    return mock.Mock()


@pytest.fixture
def vmi_synchronizer():
    return mock.Mock()


@pytest.fixture
def dvs_synchronizer():
    return mock.Mock()


@pytest.fixture
def pi_synchronizer():
    return mock.Mock()


@pytest.fixture
def synchronizer(
    database,
    vm_synchronizer,
    dpg_synchronizer,
    vpg_synchronizer,
    vmi_synchronizer,
    dvs_synchronizer,
    pi_synchronizer,
):
    return synchronizers.CVFMSynchronizer(
        database,
        vm_synchronizer,
        dpg_synchronizer,
        vpg_synchronizer,
        vmi_synchronizer,
        dvs_synchronizer,
        pi_synchronizer,
    )


def test_sync_order(
    synchronizer,
    database,
    vm_synchronizer,
    dpg_synchronizer,
    vpg_synchronizer,
    vmi_synchronizer,
    dvs_synchronizer,
    pi_synchronizer,
):
    order_checker = mock.Mock()
    order_checker.attach_mock(database, "database")
    order_checker.attach_mock(dvs_synchronizer, "dvs_synchronizer")
    order_checker.attach_mock(pi_synchronizer, "pi_synchronizer")
    order_checker.attach_mock(vm_synchronizer, "vm_synchronizer")
    order_checker.attach_mock(dpg_synchronizer, "dpg_synchronizer")
    order_checker.attach_mock(vpg_synchronizer, "vpg_synchronizer")
    order_checker.attach_mock(vmi_synchronizer, "vmi_synchronizer")

    synchronizer.sync()

    expected_order_calls = [
        mock.call.database.clear_database(),
        mock.call.dvs_synchronizer.sync(),
        mock.call.pi_synchronizer.sync(),
        mock.call.dpg_synchronizer.sync_create(),
        mock.call.vm_synchronizer.sync(),
        mock.call.vpg_synchronizer.sync_create(),
        mock.call.vmi_synchronizer.sync_create(),
        mock.call.vmi_synchronizer.sync_delete(),
        mock.call.vpg_synchronizer.sync_delete(),
        mock.call.dpg_synchronizer.sync_delete(),
    ]
    assert order_checker.mock_calls == expected_order_calls
