from builtins import zip
import mock

from pyVmomi import vim, vmodl  # pylint: disable=no-name-in-module
from vnc_api import vnc_api
from cvfm import models


def wrap_into_update_set(event=None, change=None, obj=None):
    update_set = vmodl.query.PropertyCollector.UpdateSet()
    filter_update = vmodl.query.PropertyCollector.FilterUpdate()
    if change is None:
        change = vmodl.query.PropertyCollector.Change()
        change.name = "latestPage"
        change.val = event
    object_update = mock.Mock(
        spec=vmodl.query.PropertyCollector.ObjectUpdate()
    )
    object_update.changeSet = [change]
    if obj is not None:
        object_update.obj = obj
    object_set = [object_update]
    filter_update.objectSet = object_set
    update_set.filterSet = [filter_update]
    return update_set


def create_pis_for_pr(vnc_test_client, pr, pi_nums):
    pis = {}
    for pi_num in pi_nums:
        pi_name = "xe-0/0/{}".format(pi_num)
        pi_mac = "11:22:33:44:66:{:02d}".format(pi_num)
        pi = vnc_test_client.create_physical_interface(pi_name, pi_mac, pr)
        pis[pi_num] = pi
    return pis


def create_ports_for_node(vnc_test_client, node, port_nums, port_dvses):
    ports = {}
    for port_num, dvs_name in zip(port_nums, port_dvses):
        port_name = "eth{}".format(port_num)
        port_mac = "11:22:33:44:55:{:02d}".format(port_num)
        port = vnc_test_client.create_port(port_name, port_mac, node, dvs_name)
        ports[port_num] = port
    return ports


def connect_ports_with_pis(vnc_test_client, pis, ports, port_to_pi):
    for port_num, pi_num in list(port_to_pi.items()):
        vnc_test_client.add_port_to_physical_interface(
            pis[pi_num], ports[port_num]
        )


def create_vm_created_update(vm_name, vm_host_name, vm_networks):
    event = mock.Mock(spec=vim.event.VmCreatedEvent())
    networks = [create_vmware_net(net_data) for net_data in vm_networks]
    event.vm.vm = create_vmware_vm(vm_name, vm_host_name, networks)
    return wrap_into_update_set(event=event)


def create_vmware_vm(name, host_name, networks):
    vm = mock.Mock()
    vm.config.instanceUuid = "uuid-{}".format(name)
    vm.configure_mock(name=name)
    vm.network = networks
    vm.runtime.host.name = host_name
    return vm


def create_vmware_net(net_data):
    network = mock.Mock(spec=net_data["type"])
    network.configure_mock(name=net_data["name"])
    network.key = net_data["key"]
    if net_data.get("dvs-name"):
        network.config.distributedVirtualSwitch.name = net_data["dvs-name"]
    if net_data.get("vlan"):
        network.config.defaultPortConfig.vlan.vlanId = net_data["vlan"]
    network.vm = []
    return network


def create_vm_reconfigured_update(vmware_vm, operation):
    event = mock.Mock(spec=vim.event.VmReconfiguredEvent())
    device = mock.Mock(spec=vim.vm.device.VirtualPCNet32())
    device_spec = mock.Mock(spec=vim.vm.device.VirtualDeviceSpec())
    device_spec.device = device
    device_spec.operation = operation
    event.configSpec = mock.Mock(spec=vim.vm.ConfigSpec())
    event.configSpec.deviceChange = [device_spec]
    event.vm.vm = vmware_vm
    event.vm.name = vmware_vm.name
    event.host.host = mock.Mock(vm=[vmware_vm])
    return wrap_into_update_set(event=event)


def create_host_change_update(vmware_vm, vmware_host):
    change = mock.Mock(spec=vmodl.query.PropertyCollector.Change())
    change.name = "runtime.host"
    change.val = vmware_host
    return wrap_into_update_set(change=change, obj=vmware_vm)


def create_fabric_network(vnc_test_client, vn_name, vn_key):
    project = vnc_test_client.vnc_lib.project_read(
        ["default-domain", vnc_test_client.project_name]
    )
    fab_vn = vnc_api.VirtualNetwork(name=vn_name, parent_obj=project)
    fab_vn.set_uuid(models.generate_uuid(vn_key))
    vnc_test_client.vnc_lib.virtual_network_create(fab_vn)
    return vnc_test_client.vnc_lib.virtual_network_read(id=fab_vn.uuid)


def verify_vnc_vpg(vnc_vpg, vpg_name=None, pi_names=None, vmi_names=None):
    if vpg_name is not None:
        assert vnc_vpg.name == vpg_name
    if pi_names is not None:
        pi_names = [
            pi_ref["to"][-1]
            for pi_ref in vnc_vpg.get_physical_interface_refs()
        ]
        assert sorted(pi_names) == sorted(pi_names)
    if vmi_names is not None:
        vmi_names = [
            vmi_ref["to"][-1]
            for vmi_ref in vnc_vpg.get_virtual_machine_interface_refs()
        ]
        assert sorted(vmi_names) == sorted(vmi_names)


def verify_vnc_vmi(
    vnc_vmi, vmi_name=None, vpg_name=None, vn_name=None, vlan=None
):
    if vmi_name is not None:
        assert vnc_vmi.name == vmi_name
    if vpg_name is not None:
        vpg_name = vnc_vmi.get_virtual_port_group_back_refs()[0]["to"][-1]
        assert vpg_name == vpg_name
    if vn_name is not None:
        vn_name = vnc_vmi.get_virtual_network_refs()[0]["to"][-1]
        assert vn_name == vn_name
    if vlan is not None:
        properties = vnc_vmi.get_virtual_machine_interface_properties()
        assert properties.get_sub_interface_vlan_tag() == vlan


def not_touched_in_vnc(previous, current):
    previous_mod_time = previous.get_id_perms().get_last_modified()
    current_mod_time = current.get_id_perms().get_last_modified()
    return current_mod_time == previous_mod_time


def not_deleted_from_vnc(previous, current):
    previous_create_time = previous.get_id_perms().get_created()
    current_create_time = current.get_id_perms().get_created()
    return current_create_time == previous_create_time
