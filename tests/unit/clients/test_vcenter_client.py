import mock
import pytest

from cvfm import clients


@pytest.fixture
def vcenter_api_client(vmware_dpg, vmware_vm):
    vmware_dpg.vm = [vmware_vm]
    with mock.patch("cvfm.clients.SmartConnectNoSSL") as si:
        container = mock.Mock(view=[vmware_dpg])
        content = mock.Mock()
        content.viewManager.CreateContainerView.return_value = container
        si.return_value.content = content
        return clients.VCenterAPIClient({})


def test_get_vms_for_portgroup(vcenter_api_client, vmware_vm):
    result = vcenter_api_client.get_vms_by_portgroup("dvportgroup-1")
    not_found = vcenter_api_client.get_vms_by_portgroup("dvportgroup-2")

    assert result == [vmware_vm]
    assert not_found == []
