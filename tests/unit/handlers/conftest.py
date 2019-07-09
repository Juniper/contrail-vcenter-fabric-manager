import mock
import pytest


@pytest.fixture
def vm_service():
    return mock.Mock()


@pytest.fixture
def vmi_service():
    return mock.Mock()


@pytest.fixture
def vpg_service():
    return mock.Mock()


@pytest.fixture
def dpg_service():
    return mock.Mock()


@pytest.fixture
def pi_service():
    return mock.Mock()
