import mock
import pytest

from cvfm import services


@pytest.fixture
def pi_service(vcenter_api_client, vnc_api_client, database):
    return services.PhysicalInterfaceService(
        vcenter_api_client, vnc_api_client, database
    )


def test_populate_db(pi_service, vcenter_api_client, vnc_api_client, database):
    pi_service.populate_db_with_pi_models()

    vpg_model = mock.Mock()
    pi_model = database.get_pi_models_for_vpg(vpg_model)

    assert pi_model.uuid == 'pi-1-uuid'
    assert pi_model.host_name == 'esxi-1'
    assert pi_model.dvs_name == 'dvs-1'