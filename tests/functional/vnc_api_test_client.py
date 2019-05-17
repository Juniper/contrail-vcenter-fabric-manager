from vnc_api import vnc_api


class VNCAPITestClient(object):
    def __init__(self, vnc_cfg):
        self.vnc_lib = vnc_api.VncApi(
            username=vnc_cfg.get("username"),
            password=vnc_cfg.get("password"),
            tenant_name=vnc_cfg.get("tenant_name"),
            api_server_host=vnc_cfg.get("api_server_host"),
            api_server_port=vnc_cfg.get("api_server_port"),
            auth_host=vnc_cfg.get("auth_host"),
            auth_port=vnc_cfg.get("auth_port"),
        )
        self.project_name = "test-vcenter-fabric"
        try:
            self.vnc_lib.project_create(
                vnc_api.Project(name=self.project_name)
            )
        except vnc_api.RefsExistError:
            pass

    def tear_down(self):
        self._delete_vpgs()
        self._delete_vmis()
        self._delete_vns()
        self._delete_physical_interfaces()
        self._delete_ports()
        self._delete_physical_routers()
        self._delete_nodes()
        self._delete_project()

    def _delete_ports(self):
        port_uuids = [
            port["uuid"] for port in self.vnc_lib.ports_list().get("ports")
        ]
        for port_uuid in port_uuids:
            self.delete_port(port_uuid)

    def _delete_physical_interfaces(self):
        pi_uuids = [
            pi["uuid"]
            for pi in self.vnc_lib.physical_interfaces_list().get(
                "physical-interfaces"
            )
        ]
        for pi_uuid in pi_uuids:
            self.delete_physical_interface(pi_uuid)

    def _delete_physical_routers(self):
        pr_uuids = [
            pr["uuid"]
            for pr in self.vnc_lib.physical_routers_list().get(
                "physical-routers"
            )
        ]
        for pr_uuid in pr_uuids:
            self.delete_physical_router(pr_uuid)

    def _delete_nodes(self):
        node_uuids = [
            node["uuid"] for node in self.vnc_lib.nodes_list().get("nodes")
        ]
        for node_uuid in node_uuids:
            self.delete_node(node_uuid)

    def _delete_vpgs(self):
        vpg_uuids = [
            vpg["uuid"]
            for vpg in self.vnc_lib.virtual_port_groups_list().get(
                "virtual-port-groups"
            )
        ]
        for vpg_uuid in vpg_uuids:
            vpg = self.vnc_lib.virtual_port_group_read(id=vpg_uuid)
            self._detach_vmis_from(vpg)
            self._detach_pis_from(vpg)
            self.vnc_lib.virtual_port_group_delete(id=vpg_uuid)

    def _detach_vmis_from(self, vpg):
        vmi_uuids = [ref["uuid"] for ref in
                     vpg.get_virtual_machine_interface_refs()]
        vmis = [
            self.vnc_lib.virtual_machine_interface_read(id=uuid)
            for uuid in vmi_uuids
        ]
        for vmi in vmis:
            vpg.del_virtual_machine_interface(vmi)
        self.vnc_lib.virtual_port_group_update(vpg)

    def _detach_pis_from(self, vpg):
        pi_uuids = [ref["uuid"] for ref in vpg.get_physical_interface_refs()]
        pis = [
            self.vnc_lib.physical_interface_read(id=uuid) for uuid in pi_uuids
        ]
        for pi in pis:
            vpg.del_physical_interface(pi)
        self.vnc_lib.virtual_port_group_update(vpg)

    def _delete_vmis(self):
        vmi_uuids = [
            vmi["uuid"]
            for vmi in self.vnc_lib.virtual_machine_interfaces_list(
                parent_id=self._project.uuid
            ).get("virtual-machine-interfaces")
        ]
        for vmi_uuid in vmi_uuids:
            self.vnc_lib.virtual_machine_interface_delete(id=vmi_uuid)

    def _delete_vns(self):
        vn_uuids = [
            vn["uuid"]
            for vn in self.vnc_lib.virtual_networks_list(
                parent_id=self._project.uuid
            ).get("virtual-networks")
        ]
        for vn_uuid in vn_uuids:
            self.vnc_lib.virtual_network_delete(id=vn_uuid)

    def _delete_project(self):
        project_uuid = self._project.uuid
        try:
            self.vnc_lib.project_delete(id=project_uuid)
        except vnc_api.NoIdError:
            pass

    @property
    def _project(self):
        return self.vnc_lib.project_read(["default-domain", self.project_name])

    def create_physical_router(self, pr_name):
        physical_router = vnc_api.PhysicalRouter(pr_name)
        uuid = self.vnc_lib.physical_router_create(physical_router)
        return self.read_physical_router(uuid)

    def read_physical_router(self, pr_uuid):
        return self.vnc_lib.physical_router_read(id=pr_uuid)

    def delete_physical_router(self, pr_uuid):
        self.vnc_lib.physical_router_delete(id=pr_uuid)

    def create_physical_interface(self, pi_name, mac_address, physical_router):
        physical_interface = vnc_api.PhysicalInterface(
            name=pi_name,
            parent_obj=physical_router,
            physical_interface_mac_addresses={"mac_address": [mac_address]},
        )
        pi_uuid = self.vnc_lib.physical_interface_create(physical_interface)
        return self.read_physical_interface(pi_uuid)

    def read_physical_interface(self, pi_uuid):
        return self.vnc_lib.physical_interface_read(id=pi_uuid)

    def delete_physical_interface(self, pi_uuid):
        self.vnc_lib.physical_interface_delete(id=pi_uuid)

    def create_node(self, node_name, node_ip):
        esxi_host_info = vnc_api.ESXIHostInfo(esxi_name=node_ip)
        node = vnc_api.Node(name=node_name, esxi_info=esxi_host_info)
        node_uuid = self.vnc_lib.node_create(node)
        return self.read_node(node_uuid)

    def read_node(self, node_uuid):
        return self.vnc_lib.node_read(id=node_uuid)

    def delete_node(self, node_uuid):
        self.vnc_lib.node_delete(id=node_uuid)

    def create_port(self, port_name, mac_address, node, dvs_list):
        port_info = vnc_api.BaremetalPortInfo(address=mac_address)
        port = vnc_api.Port(port_name, node, bms_port_info=port_info)
        port_uuid = self.vnc_lib.port_create(port)
        port = self.read_port(port_uuid)
        annotations = [
            vnc_api.KeyValuePair(key=dvs_name, value="vmware_dvs")
            for dvs_name in dvs_list
        ]
        annotations = vnc_api.KeyValuePairs(key_value_pair=annotations)
        port.annotations = annotations
        self.vnc_lib.port_update(port)
        return self.read_port(port_uuid)

    def read_port(self, port_uuid):
        return self.vnc_lib.port_read(id=port_uuid)

    def delete_port(self, port_uuid):
        return self.vnc_lib.port_delete(id=port_uuid)

    def add_port_to_physical_interface(self, pi, port):
        pi.add_port(port)
        self.vnc_lib.physical_interface_update(pi)

    def add_connection_between_pis(self, pi_1, pi_2):
        pi_1.add_physical_interface(pi_2)
        self.vnc_lib.physical_interface_update(pi_1)
        pi_2.add_physical_interface(pi_1)
        self.vnc_lib.physical_interface_update(pi_2)
