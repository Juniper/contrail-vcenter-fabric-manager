import mock
import pytest
from vnc_api import vnc_api
from pyVmomi import vim

from cvfm import models, controllers
from tests import utils


@pytest.fixture
def update_handler(vmi_service, vpg_service):
    vm_updated_handler = controllers.VmUpdatedHandler(
        None, vmi_service, None, vpg_service
    )
    vm_removed_handler = controllers.VmRemovedHandler(
        None, vmi_service, None, vpg_service
    )
    return controllers.UpdateHandler([vm_updated_handler, vm_removed_handler])


@pytest.fixture
def vm_removed_update():
    event = mock.Mock(spec=vim.event.VmRemovedEvent())
    event.vm.name = "vm-1"
    event.host.name = "esxi-1"
    return utils.wrap_into_update_set(event=event)


@pytest.fixture
def vm_created_update():
    networks = [
        {
            "key": "dvportgroup-1",
            "name": "dpg-1",
            "type": vim.DistributedVirtualPortgroup,
            "dvs-name": "dvs-1",
            "vlan": 5,
        }
    ]
    return utils.create_vm_created_update(
        vm_name="VM1", vm_host_name="esxi-1", vm_networks=networks
    )


@pytest.mark.skip
def test_last_vm_from_pg(
    minimalistic_topology,
    fabric_vn,
    vmware_controller,
    vm_created_update,
    vm_removed_update,
    vnc_test_client,
):
    vmware_controller.handle_update(vm_created_update)
    vnc_vpg = vnc_test_client.vnc_lib.virtual_port_group_read(
        id=models.generate_uuid("esxi-1_dvs-1")
    )
    vnc_vmi = vnc_test_client.vnc_lib.virtual_machine_interface_read(
        id=models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )

    assert vnc_vpg is not None
    assert vnc_vmi is not None

    vmware_controller.handle_update(vm_removed_update)

    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.vnc_lib.virtual_port_group_read(id=vnc_vpg.uuid)
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.vnc_lib.virtual_machine_interface_read(id=vnc_vmi.uuid)


@pytest.mark.skip
def test_vms_remaining_in_pg(
    minimalistic_topology,
    fabric_vn,
    vmware_controller,
    vm_created_update,
    vm_removed_update,
    vnc_test_client,
):
    vmware_controller.handle_update(vm_created_update)
    vnc_vpg = vnc_test_client.vnc_lib.virtual_port_group_read(
        id=models.generate_uuid("esxi-1_dvs-1")
    )
    vnc_vmi = vnc_test_client.vnc_lib.virtual_machine_interface_read(
        id=models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert vnc_vpg is not None
    assert vnc_vmi is not None

    vmware_controller.handle_update(vm_removed_update)

    vpg = vnc_test_client.vnc_lib.virtual_port_group_read(id=vnc_vpg.uuid)
    vmi = vnc_test_client.vnc_lib.virtual_machine_interface_read(
        id=vnc_vmi.uuid
    )

    assert vpg is not None
    assert vmi is not None
