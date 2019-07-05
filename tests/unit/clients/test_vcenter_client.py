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


@mock.patch("cvfm.clients.time.sleep")
def test_is_vm_removed(_, vcenter_api_client, vmware_vm):
    vcenter_api_client._get_vm_by_name = mock.Mock()

    vcenter_api_client._get_vm_by_name.return_value = vmware_vm
    # VM vm-1 still exists on esxi-1
    assert not vcenter_api_client.is_vm_removed(vmware_vm, "esxi-2")

    vcenter_api_client._get_vm_by_name.return_value = None
    # VM vm-1 was removed from host esxi-1 and whole vCenter
    assert vcenter_api_client.is_vm_removed(vmware_vm, "esxi-1")
