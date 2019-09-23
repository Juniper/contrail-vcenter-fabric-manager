from builtins import object
from vnc_api import vnc_api


class VNCAPITestClient(object):
    def __init__(self, vnc_cfg, auth_cfg=None):
        if auth_cfg is None:
            auth_cfg = {}
        self.vnc_lib = vnc_api.VncApi(
            api_server_host=vnc_cfg.get("api_server_host"),
            api_server_port=vnc_cfg.get("api_server_port"),
            api_server_use_ssl=vnc_cfg.get("api_server_use_ssl"),
            apicertfile=vnc_cfg.get("api_certfile"),
            apikeyfile=vnc_cfg.get("api_keyfile"),
            apicafile=vnc_cfg.get("api_cafile"),
            apiinsecure=vnc_cfg.get("api_server_insecure"),
            username=auth_cfg.get("auth_user"),
            password=auth_cfg.get("auth_password"),
            tenant_name=auth_cfg.get("auth_tenant"),
            auth_token_url=auth_cfg.get("auth_token_url"),
        )
        self.project_name = vnc_cfg.get("project_name", "test-vcenter-fabric")
        try:
            self.vnc_lib.project_create(
                vnc_api.Project(name=self.project_name)
            )
        except vnc_api.RefsExistError:
            pass
        self.fabric_name = vnc_cfg.get("fabric_name", "test-fabric")
        self.create_fabric()

    def tear_down(self):
        self._delete_vpgs()
        self._delete_vmis()
        self._delete_vns()
        self._delete_physical_interfaces()
        self._delete_ports()
        self._delete_physical_routers()
        self._delete_nodes()
        self._delete_project()
        self._delete_fabric()

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
        vmi_refs = vpg.get_virtual_machine_interface_refs() or []
        vmi_uuids = [ref["uuid"] for ref in vmi_refs]
        vmis = [
            self.vnc_lib.virtual_machine_interface_read(id=uuid)
            for uuid in vmi_uuids
        ]
        for vmi in vmis:
            vpg.del_virtual_machine_interface(vmi)
        self.vnc_lib.virtual_port_group_update(vpg)

    def _detach_pis_from(self, vpg):
        pi_refs = vpg.get_physical_interface_refs() or []
        pi_uuids = [ref["uuid"] for ref in pi_refs]
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

    def _delete_fabric(self):
        fabric_uuid = self.fabric.uuid
        try:
            self.vnc_lib.fabric_delete(id=fabric_uuid)
        except vnc_api.NoIdError:
            pass

    @property
    def _project(self):
        return self.vnc_lib.project_read(["default-domain", self.project_name])

    @property
    def fabric(self):
        return self.vnc_lib.fabric_read(
            ["default-global-system-config", self.fabric_name]
        )

    def create_fabric(self):
        try:
            fabric = vnc_api.Fabric(self.fabric_name)
            uuid = self.vnc_lib.fabric_create(fabric)
            return self.vnc_lib.fabric_read(id=uuid)
        except vnc_api.RefsExistError:
            pass

    def create_physical_router(self, pr_name, fabric):
        physical_router = vnc_api.PhysicalRouter(pr_name)
        physical_router.add_fabric(fabric)
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

    def read_all_physical_interface_uuids(self):
        return [
            pi["uuid"]
            for pi in self.vnc_lib.physical_interfaces_list()[
                "physical-interfaces"
            ]
        ]

    def read_all_physical_interfaces(self):
        return [
            self.read_physical_interface(pi_uuid)
            for pi_uuid in self.read_all_physical_interface_uuids()
        ]

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

    def create_port(self, port_name, mac_address, node, dvs_name):
        bms_port_info = vnc_api.BaremetalPortInfo(address=mac_address)
        esxi_port_info = vnc_api.ESXIProperties(dvs_name=dvs_name)
        port = vnc_api.Port(
            name=port_name,
            parent_obj=node,
            bms_port_info=bms_port_info,
            esxi_port_info=esxi_port_info,
        )
        port_uuid = self.vnc_lib.port_create(port)
        return self.read_port(port_uuid)

    def update_ports_dvs_name(self, port_uuid, dvs_name):
        port = self.read_port(port_uuid)
        esxi_port_info = vnc_api.ESXIProperties(dvs_name=dvs_name)
        port.set_esxi_port_info(esxi_port_info)
        self.vnc_lib.port_update(port)

    def read_port(self, port_uuid):
        return self.vnc_lib.port_read(id=port_uuid)

    def delete_port(self, port_uuid):
        return self.vnc_lib.port_delete(id=port_uuid)

    def add_port_to_physical_interface(self, pi, port):
        pi.add_port(port)
        self.vnc_lib.physical_interface_update(pi)

    def remove_ports_from_physical_interface(self, pi):
        port_refs = pi.get_port_refs()
        ports = [self.read_port(port_ref["uuid"]) for port_ref in port_refs]
        for port in ports:
            pi.del_port(port)
        self.vnc_lib.physical_interface_update(pi)

    def add_connection_between_pis(self, pi_1, pi_2):
        pi_1.add_physical_interface(pi_2)
        self.vnc_lib.physical_interface_update(pi_1)
        pi_2.add_physical_interface(pi_1)
        self.vnc_lib.physical_interface_update(pi_2)

    def create_vpg(self, vnc_vpg):
        self.vnc_lib.virtual_port_group_create(vnc_vpg)

    def read_vpg(self, vpg_uuid):
        return self.vnc_lib.virtual_port_group_read(id=vpg_uuid)

    def read_all_vpgs(self):
        vpg_refs = self.vnc_lib.virtual_port_groups_list()[
            "virtual-port-groups"
        ]
        vpg_list = [self.read_vpg(vpg_ref["uuid"]) for vpg_ref in vpg_refs]
        return {vpg.name: vpg for vpg in vpg_list}

    def read_vmi(self, vmi_uuid):
        return self.vnc_lib.virtual_machine_interface_read(id=vmi_uuid)

    def read_all_vmis(self):
        vmi_refs = self.vnc_lib.virtual_machine_interfaces_list(
            parent_id=self._project.get_uuid()
        )["virtual-machine-interfaces"]
        vmi_list = [self.read_vmi(vmi_ref["uuid"]) for vmi_ref in vmi_refs]
        return {vmi.name: vmi for vmi in vmi_list}

    def read_vn(self, vn_uuid):
        return self.vnc_lib.virtual_network_read(id=vn_uuid)
