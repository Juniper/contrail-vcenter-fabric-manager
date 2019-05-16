import pytest

from cvfm.services import DistributedPortGroupService


@pytest.fixture
def dpg_service(vnc_api_client):
    return DistributedPortGroupService(None, vnc_api_client, None)


def test_find_matches_physical_interfaces(
    topology_with_spine_switch, dpg_service
):

    pis = dpg_service.find_matches_physical_interfaces("esxi-1", "dvs-1")
    check_pi_names(pis, ["xe-0/0/1", "xe-0/0/5"])

    pis = dpg_service.find_matches_physical_interfaces("esxi-1", "dvs-2")
    check_pi_names(pis, ["xe-0/0/2", "xe-0/0/6"])

    pis = dpg_service.find_matches_physical_interfaces("esxi-2", "dvs-1")
    check_pi_names(pis, ["xe-0/0/3", "xe-0/0/7"])

    pis = dpg_service.find_matches_physical_interfaces("esxi-2", "dvs-2")
    check_pi_names(pis, ["xe-0/0/4", "xe-0/0/8"])

    pis = dpg_service.find_matches_physical_interfaces("esxi-1", "dvs-3")
    check_pi_names(pis, [])

    pis = dpg_service.find_matches_physical_interfaces("esxi-3", "dvs-1")
    check_pi_names(pis, [])


def check_pi_names(pis, expected_pi_names):
    assert len(pis) == len(expected_pi_names)
    pi_names = sorted(pi.name for pi in pis)
    assert pi_names == expected_pi_names
