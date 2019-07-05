import mock
import pytest


@pytest.fixture
def dvs_service():
    return mock.Mock()


def test_sync(dvs_synchronizer, dvs_service):
    dvs_synchronizer.sync()

    dvs_service.populate_db_with_supported_dvses.assert_called_once()
