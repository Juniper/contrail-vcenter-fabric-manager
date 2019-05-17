import mock

from pyVmomi import vim, vmodl  # pylint: disable=no-name-in-module
from vnc_api import vnc_api


def wrap_into_update_set(event=None, change=None, obj=None):
    update_set = vmodl.query.PropertyCollector.UpdateSet()
    filter_update = vmodl.query.PropertyCollector.FilterUpdate()
    if change is None:
        change = vmodl.query.PropertyCollector.Change()
        change.name = "latestPage"
        change.val = event
    object_update = vmodl.query.PropertyCollector.ObjectUpdate()
    object_update.changeSet = [change]
    if obj is not None:
        object_update.obj = obj
    object_set = [object_update]
    filter_update.objectSet = object_set
    update_set.filterSet = [filter_update]
    return update_set


def prepare_annotations(raw_annotations):
    annotations = []
    for key, value in raw_annotations.items():
        annotations.append(vnc_api.KeyValuePair(key=key, value=value))
    annotations = vnc_api.KeyValuePairs(key_value_pair=annotations)
    return annotations


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
    for port_num, dvses in zip(port_nums, port_dvses):
        port_name = "eth{}".format(port_num)
        port_mac = "11:22:33:44:55:{:02d}".format(port_num)
        port = vnc_test_client.create_port(port_name, port_mac, node, dvses)
        ports[port_num] = port
    return ports


def connect_ports_with_pis(vnc_test_client, pis, ports, port_to_pi):
    for port_num, pi_num in port_to_pi.items():
        vnc_test_client.add_port_to_physical_interface(
            pis[pi_num], ports[port_num]
        )


def create_vm_created_update(vm_name, vm_host_name, vm_networks):
    event = mock.Mock(spec=vim.event.VmCreatedEvent())
    vm = mock.Mock()
    vm.name = vm_name
    networks = []
    for net_data in vm_networks:
        network = mock.Mock(spec=net_data["type"])
        network.configure_mock(name=net_data["name"])
        network.key = net_data["key"]
        if net_data.get("dvs-name"):
            network.config.distributedVirtualSwitch.name = net_data["dvs-name"]
        if net_data.get("vlan"):
            network.config.defaultPortConfig.vlan.vlanId = net_data["vlan"]
        networks.append(network)
    vm.network = networks
    vm.runtime.host.name = vm_host_name
    vm.name = vm_name
    event.vm.vm = vm
    return wrap_into_update_set(event=event)


def verify_vnc_vpg(vnc_vpg, vpg_name=None, pi_names=None, vmi_names=None):
    if pi_names is not None:
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
