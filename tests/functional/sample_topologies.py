import pytest

from tests import utils

__all__ = [
    "minimalistic_topology",
    "topology_with_two_nodes",
    "topology_with_spine_switch",
    "dvs_per_esxi_topology",
]


@pytest.fixture
def minimalistic_topology(vnc_test_client, vcenter_api_client):
    """
    Topology:
        esxi-1:port-1:dvs-1:pi-1:pr-1

        esxi-1:
            name: esxi-1
            ip: 10.10.10.11
        port-1:
            name: eth0
            mac_address: 11:22:33:44:55:01
        dvs-1:
            name: dvs-1
        pi-1:
            name: xe-0/0/0
            mac_address: 11:22:33:44:55:02
        pr-1:
            name: qfx-1
    """
    fabric = vnc_test_client.fabric
    pr = vnc_test_client.create_physical_router("qfx-1", fabric)
    pi = vnc_test_client.create_physical_interface(
        "xe-0/0/0", "11:22:33:44:55:02", pr
    )
    node = vnc_test_client.create_node("esxi-1", "10.10.10.11")
    port = vnc_test_client.create_port(
        "eth0", "11:22:33:44:55:01", node, "dvs-1"
    )
    vnc_test_client.add_port_to_physical_interface(pi, port)

    vcenter_api_client.add_host("esxi-1")


@pytest.fixture
def topology_with_two_nodes(vnc_test_client, vcenter_api_client):
    """
    Topology:
        esxi-1:port-1:dvs-1:pi-1:pr-1
        esxi-2:port-2:dvs-1:pi-2:pr-1

        esxi-1:
            name: esxi-1
            ip: 10.10.10.11
        esxi-2:
            name: esxi-2
            ip: 10.10.10.12
        port-1:
            name: eth1
            mac_address: 11:22:33:44:55:01
        port-2:
            name: eth2
            mac_address: 11:22:33:44:55:02
        dvs-1:
            name: dvs-1
        pi-1:
            name: xe-0/0/1
            mac_address: 11:22:33:44:55:68
        pi-2:
            name: xe-0/0/2
            mac_address: 11:22:33:44:55:69
        pr-1:
            name: qfx-1
    """
    fabric = vnc_test_client.fabric
    pr = vnc_test_client.create_physical_router("qfx-1", fabric)
    pi_1 = vnc_test_client.create_physical_interface(
        "xe-0/0/1", "11:22:33:44:55:68", pr
    )
    pi_2 = vnc_test_client.create_physical_interface(
        "xe-0/0/2", "11:22:33:44:55:69", pr
    )
    esxi_1 = vnc_test_client.create_node("esxi-1", "10.10.10.11")
    esxi_2 = vnc_test_client.create_node("esxi-2", "10.10.10.12")
    port_1 = vnc_test_client.create_port(
        "eth1", "11:22:33:44:55:01", esxi_1, "dvs-1"
    )
    port_2 = vnc_test_client.create_port(
        "eth2", "11:22:33:44:55:02", esxi_2, "dvs-1"
    )
    vnc_test_client.add_port_to_physical_interface(pi_1, port_1)
    vnc_test_client.add_port_to_physical_interface(pi_2, port_2)

    vcenter_api_client.add_host("esxi-1")
    vcenter_api_client.add_host("esxi-2")


@pytest.fixture
def topology_with_spine_switch(vnc_test_client, vcenter_api_client):
    """
    Topology:
        esxi-1:port-1:dvs-1:pi-1:pr-1
        esxi-1:port-2:dvs-2:pi-2:pr-1
        esxi-1:port-3:dvs-1:pi-5:pr-2
        esxi-1:port-4:dvs-2:pi-6:pr-2

        esxi-2:port-5:dvs-1:pi-3:pr-1
        esxi-2:port-6:dvs-2:pi-4:pr-1
        esxi-2:port-7:dvs-1:pi-7:pr-2
        esxi-2:port-8:dvs-2:pi-8:pr-2

        pr-1:pi-9:pi-11:pr-3
        pr-2:pi-10:pi-12:pr-3

        esxi-1:
            name: esxi-1
            ip: 10.10.10.11
        esxi-2:
            name: esxi-2
            ip: 10.10.10.12
        port-*:
            name: eth*
            mac_address: 11:22:33:44:55:*
        pi-*:;
            max: xe-0/0/*
            mac_address: 11:22:33:44:66:*
        pr-1:
            name: qfx-leaf-1
        pr-2:
            name: qfx-leaf-2
        pr-3:
            name: qfx-spine
    """
    fabric = vnc_test_client.fabric
    pr_spine = vnc_test_client.create_physical_router("qfx-spine", fabric)
    pr_leaf_1 = vnc_test_client.create_physical_router("qfx-leaf-1", fabric)
    pr_leaf_2 = vnc_test_client.create_physical_router("qfx-leaf-2", fabric)

    leaf_1_pi_nums = [1, 2, 3, 4, 9]
    leaf_1_pis = utils.create_pis_for_pr(
        vnc_test_client, pr_leaf_1, leaf_1_pi_nums
    )
    leaf_2_pi_nums = [5, 6, 7, 8, 10]
    leaf_2_pis = utils.create_pis_for_pr(
        vnc_test_client, pr_leaf_2, leaf_2_pi_nums
    )
    spine_pi_nums = [11, 12]
    spine_pis = utils.create_pis_for_pr(
        vnc_test_client, pr_spine, spine_pi_nums
    )
    vnc_test_client.add_connection_between_pis(leaf_1_pis[9], spine_pis[11])
    vnc_test_client.add_connection_between_pis(leaf_2_pis[10], spine_pis[12])

    esxi_1 = vnc_test_client.create_node("esxi-1", "10.10.10.11")
    esxi_2 = vnc_test_client.create_node("esxi-2", "10.10.10.12")
    port_dvses = ["dvs-1", "dvs-2", "dvs-1", "dvs-2"]

    esxi_1_port_nums = [1, 2, 3, 4]
    esxi_1_ports = utils.create_ports_for_node(
        vnc_test_client, esxi_1, esxi_1_port_nums, port_dvses
    )

    esxi_2_ports_nums = [5, 6, 7, 8]
    esxi_2_ports = utils.create_ports_for_node(
        vnc_test_client, esxi_2, esxi_2_ports_nums, port_dvses
    )

    pis = dict(
        list(leaf_1_pis.items())
        + list(leaf_2_pis.items())
        + list(spine_pis.items())
    )
    ports = dict(list(esxi_1_ports.items()) + list(esxi_2_ports.items()))
    port_to_pi = {1: 1, 2: 2, 3: 5, 4: 6, 5: 3, 6: 4, 7: 7, 8: 8}
    utils.connect_ports_with_pis(vnc_test_client, pis, ports, port_to_pi)

    vcenter_api_client.add_host("esxi-1")
    vcenter_api_client.add_host("esxi-2")


@pytest.fixture
def dvs_per_esxi_topology(vnc_test_client, vcenter_api_client):
    """
    Topology:
        esxi-1:port-1:dvs-1:pi-1:pr-1
        esxi-2:port-2:dvs-2:pi-2:pr-1

        esxi-1:
            name: esxi-1
            ip: 10.10.10.11
        esxi-2:
            name: esxi-2
            ip: 10.10.10.12
        port-*:
            name: eth*
            mac_address: 11:22:33:44:55:*
        pi-*:;
            max: xe-0/0/*
            mac_address: 11:22:33:44:66:*
        pr-1:
            name: qfx-1
    """
    fabric = vnc_test_client.fabric
    pr = vnc_test_client.create_physical_router("qfx-1", fabric)
    pi_1 = vnc_test_client.create_physical_interface(
        "xe-0/0/1", "11:22:33:44:55:68", pr
    )
    pi_2 = vnc_test_client.create_physical_interface(
        "xe-0/0/2", "11:22:33:44:55:69", pr
    )
    esxi_1 = vnc_test_client.create_node("esxi-1", "10.10.10.11")
    esxi_2 = vnc_test_client.create_node("esxi-2", "10.10.10.12")
    port_1 = vnc_test_client.create_port(
        "eth1", "11:22:33:44:55:01", esxi_1, "dvs-1"
    )
    port_2 = vnc_test_client.create_port(
        "eth2", "11:22:33:44:55:02", esxi_2, "dvs-2"
    )
    vnc_test_client.add_port_to_physical_interface(pi_1, port_1)
    vnc_test_client.add_port_to_physical_interface(pi_2, port_2)

    vcenter_api_client.add_host("esxi-1")
    vcenter_api_client.add_host("esxi-2")
