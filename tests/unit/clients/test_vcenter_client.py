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
        content.searchIndex.FindByUuid.return_value = vmware_vm
        si.return_value.content = content
        return clients.VCenterAPIClient({})


def test_get_vms_for_portgroup(vcenter_api_client, vmware_vm):
    result = vcenter_api_client.get_vms_by_portgroup("dvportgroup-1")
    not_found = vcenter_api_client.get_vms_by_portgroup("dvportgroup-2")

    assert result == [vmware_vm]
    assert not_found == []


@mock.patch("cvfm.clients.time.sleep")
def test_is_vm_removed(_, vcenter_api_client, vmware_vm):
    # VM vm-1 still exists on esxi-1
    assert not vcenter_api_client.is_vm_removed(
        vmware_vm.config.instanceUuid, "esxi-1"
    )

    # VM vm-1 was removed from host esxi-1 and whole vCenter
    with mock.patch.object(vcenter_api_client, "_si") as si:
        si.content.searchIndex.FindByUuid.return_value = None
        assert vcenter_api_client.is_vm_removed(
            vmware_vm.config.instanceUuid, "esxi-1"
        )
