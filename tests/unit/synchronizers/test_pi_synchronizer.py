import mock
import pytest


@pytest.fixture
def pi_service():
    return mock.Mock()


def test_sync(pi_synchronizer, pi_service):
    pi_synchronizer.sync()

    pi_service.populate_db_with_pi_models.assert_called_once()
