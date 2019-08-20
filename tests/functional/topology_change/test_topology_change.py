import gevent
import mock
import pytest

from pyVmomi import vim
from tests import utils
from cvfm import monitors, controllers
from cvfm.clients.rabbit import VNCRabbitClient

import gevent.monkey

gevent.monkey.patch_all()


@pytest.fixture
def vmware_vm_1(vmware_dpg_1):
    return utils.create_vmware_vm("vm-1", "esxi-1", [vmware_dpg_1])


@pytest.fixture
def vmware_vm_2(vmware_dpg_2):
    return utils.create_vmware_vm("vm-2", "esxi-2", [vmware_dpg_2])


@pytest.fixture
def vmware_dpg_1():
    net_data = {
        "key": "dvportgroup-1",
        "name": "dpg-1",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-1",
        "vlan": 5,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_dpg_2():
    net_data = {
        "key": "dvportgroup-2",
        "name": "dpg-2",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-2",
        "vlan": 6,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vnc_rabbit_client(config):
    return VNCRabbitClient(config["rabbit_config"])


@pytest.fixture
def vnc_monitor(vnc_rabbit_client, vmware_controller):
    return monitors.VNCMonitor(vmware_controller, vnc_rabbit_client)


@pytest.fixture
def context(vnc_monitor, vcenter_api_client):
    with mock.patch.object(
        vcenter_api_client, "wait_for_updates", return_value=None
    ):
        gevent.joinall([gevent.spawn(vnc_monitor.start)], raise_error=True)


@pytest.fixture
def vmware_controller(synchronizer, update_handler, lock, sync_finished):
    controller = VMwareMockController(
        synchronizer, update_handler, lock, sync_finished
    )
    controller.sync()
    controller.clear_sync_finished_flag()
    return controller


@pytest.fixture
def lock():
    return gevent.lock.BoundedSemaphore()


@pytest.fixture
def sync_finished():
    return gevent.event.Event()


@mock.patch("cvfm.constants.TOPOLOGY_UPDATE_MESSAGE_TIMEOUT")
def test_add_new_node(
    topology_update_msg_timeout,
    minimalistic_topology,
    vnc_test_client,
    vmware_controller,
    vcenter_api_client,
    vmware_dpg_1,
    vmware_dpg_2,
    vmware_vm_1,
    vmware_vm_2,
    vnc_monitor,
    lock,
    sync_finished,
):
    topology_update_msg_timeout = 1
    vnc_monitor_greenlet = gevent.spawn(vnc_monitor.start)

    # create a DPG
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_1)
    vmware_controller.handle_update(dpg_created_update)
    # create a VM in a DPG
    vm_created_update = vcenter_api_client.create_vm(vmware_vm_1)
    vmware_controller.handle_update(vm_created_update)

    with lock:
        # change topology - add a new node and a new dvs supported by this node
        existing_pi_uuid = vnc_test_client.read_all_physical_interface_uuids()[
            0
        ]
        existing_pi = vnc_test_client.read_physical_interface(existing_pi_uuid)
        pr = vnc_test_client.read_physical_router(existing_pi.parent_uuid)
        pi = vnc_test_client.create_physical_interface(
            "xe-0/0/1", "11:22:33:44:55:03", pr
        )
        esxi = vnc_test_client.create_node("esxi-2", "10.10.10.12")
        port = vnc_test_client.create_port(
            "eth1", "11:22:33:44:55:01", esxi, "dvs-2"
        )
        vnc_test_client.add_port_to_physical_interface(pi, port)
        vcenter_api_client.add_host("esxi-2")

    sync_finished.wait()

    # create a new DPG in the new DVS
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_2)
    vmware_controller.handle_update(dpg_created_update)
    # create a new VM in the new DPG
    vm_created_update = vcenter_api_client.create_vm(vmware_vm_2)
    vmware_controller.handle_update(vm_created_update)

    # verify that VPGs and VMIs exist for all VMs and DPGs
    vmis = vnc_test_client.read_all_vmis()
    assert len(vmis) == 2
    vpgs = vnc_test_client.read_all_vpgs()
    assert len(vpgs) == 2

    created_vpg_1 = vpgs["esxi-1_dvs-1"]
    created_vmi_1 = vmis["esxi-1_dvs-1_dpg-1"]

    created_vpg_2 = vpgs["esxi-2_dvs-2"]
    created_vmi_2 = vmis["esxi-2_dvs-2_dpg-2"]

    utils.verify_vnc_vpg(
        vnc_vpg=created_vpg_1,
        vpg_name="esxi-1_dvs-1",
        pi_names=["xe-0/0/0"],
        vmi_names=["esxi-1_dvs-1_dpg-1"],
    )

    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi_1,
        vmi_name="esxi-1_dvs-1_dpg-1",
        vpg_name="esxi-1_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=5,
    )

    utils.verify_vnc_vpg(
        vnc_vpg=created_vpg_2,
        vpg_name="esxi-2_dvs-2",
        pi_names=["xe-0/0/1"],
        vmi_names=["esxi-2_dvs-2_dpg-2"],
    )

    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi_2,
        vmi_name="esxi-2_dvs-2_dpg-2",
        vpg_name="esxi-2_dvs-2",
        vn_name="dvs-2_dpg-2",
        vlan=6,
    )

    vnc_monitor_greenlet.kill()


@mock.patch("cvfm.constants.TOPOLOGY_UPDATE_MESSAGE_TIMEOUT")
def test_remove_node(
    topology_update_msg_timeout,
    topology_with_two_nodes,
    vnc_test_client,
    vmware_controller,
    vcenter_api_client,
    vmware_dpg_1,
    vmware_dpg_2,
    vmware_vm_1,
    vmware_vm_2,
    vnc_monitor,
    lock,
    sync_finished,
):
    topology_update_msg_timeout = 1
    vnc_monitor_greenlet = gevent.spawn(vnc_monitor.start)

    # create a DPG
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_1)
    vmware_controller.handle_update(dpg_created_update)
    # create a VM in a DPG
    vm_created_update = vcenter_api_client.create_vm(vmware_vm_1)
    vmware_controller.handle_update(vm_created_update)

    # create a new DPG in the new DVS
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_2)
    vmware_controller.handle_update(dpg_created_update)
    # create a new VM in the new DPG
    vm_created_update = vcenter_api_client.create_vm(vmware_vm_2)
    vmware_controller.handle_update(vm_created_update)

    with lock:
        # change topology - remove a node (esxi-2) and a dvs (dvs-2) supported
        # by this node
        vnc_test_client.vnc_lib.physical_interface_delete(
            ["default-global-system-config", "qfx-1", "xe-0/0/2"]
        )

        vnc_test_client.vnc_lib.port_delete(
            ["default-global-system-config", "esxi-2", "eth2"]
        )

        vnc_test_client.vnc_lib.node_delete(
            ["default-global-system-config", "esxi-2"]
        )

    sync_finished.wait()

    # verify that VPGs and VMIs exist for all VMs and DPGs
    vmis = vnc_test_client.read_all_vmis()
    assert len(vmis) == 1
    vpgs = vnc_test_client.read_all_vpgs()
    assert len(vpgs) == 1

    created_vpg_1 = vpgs["esxi-1_dvs-1"]
    created_vmi_1 = vmis["esxi-1_dvs-1_dpg-1"]

    utils.verify_vnc_vpg(
        vnc_vpg=created_vpg_1,
        vpg_name="esxi-1_dvs-1",
        pi_names=["xe-0/0/0"],
        vmi_names=["esxi-1_dvs-1_dpg-1"],
    )

    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi_1,
        vmi_name="esxi-1_dvs-1_dpg-1",
        vpg_name="esxi-1_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=5,
    )

    vnc_monitor_greenlet.kill()


class VMwareMockController(controllers.VMwareController):
    def __init__(self, synchronizer, update_handler, lock, sync_finished):
        super(VMwareMockController, self).__init__(
            synchronizer, update_handler, lock
        )
        self._sync_finished = sync_finished

    def sync(self):
        super(VMwareMockController, self).sync()
        self._sync_finished.set()

    def clear_sync_finished_flag(self):
        self._sync_finished.clear()
