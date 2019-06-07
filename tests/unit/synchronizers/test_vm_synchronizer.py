import mock
import pytest


@pytest.fixture
def vm_service():
    return mock.Mock()


def test_sync(vm_synchronizer, vm_service):
    vm_synchronizer.sync()

    vm_service.populate_db.assert_called_once()
