import atexit
import logging
import time

from pyVim.connect import Disconnect, SmartConnectNoSSL
from pyVmomi import vim, vmodl  # pylint: disable=no-name-in-module
from vnc_api import vnc_api

from cvfm import constants as const

logger = logging.getLogger(__name__)


def make_prop_set(obj, filters):
    prop_set = []
    property_spec = vmodl.query.PropertyCollector.PropertySpec(
        type=type(obj), all=False
    )
    property_spec.pathSet.extend(filters)
    prop_set.append(property_spec)
    return prop_set


def make_object_set(obj):
    object_set = [vmodl.query.PropertyCollector.ObjectSpec(obj=obj)]
    return object_set


def make_filter_spec(obj, filters):
    filter_spec = vmodl.query.PropertyCollector.FilterSpec()
    filter_spec.objectSet = make_object_set(obj)
    filter_spec.propSet = make_prop_set(obj, filters)
    return filter_spec


def has_proper_creator(vnc_object):
    id_perms = vnc_object.get_id_perms()
    if id_perms is not None:
        return id_perms.get_creator() == const.ID_PERMS.get_creator()
    return False


class VCenterAPIClient(object):
    def __init__(self, vcenter_cfg):
        super(VCenterAPIClient, self).__init__()
        self._vcenter_cfg = vcenter_cfg
        self._create_connection()

    def _create_connection(self):
        self._si = SmartConnectNoSSL(
            host=self._vcenter_cfg.get("vc_host"),
            user=self._vcenter_cfg.get("vc_username"),
            pwd=self._vcenter_cfg.get("vc_password"),
            port=self._vcenter_cfg.get("vc_port"),
            preferredApiVersions=self._vcenter_cfg.get(
                "vc_preferred_api_versions"
            ),
        )
        atexit.register(Disconnect, self._si)
        self._datacenter = self._get_datacenter(
            self._vcenter_cfg.get("vc_datacenter")
        )
        self._property_collector = self._si.content.propertyCollector
        self._wait_options = vmodl.query.PropertyCollector.WaitOptions()
        self._version = ""
        self._pg_view = self._create_view(
            [vim.dvs.DistributedVirtualPortgroup]
        )
        self._vm_view = self._create_view([vim.VirtualMachine])
        self._host_view = self._create_view([vim.HostSystem])

    def _create_view(self, vimtype):
        return self._si.content.viewManager.CreateContainerView(
            self._datacenter, vimtype, True
        )

    def _get_datacenter(self, name):
        container = self._si.content.viewManager.CreateContainerView(
            self._si.content.rootFolder, [vim.Datacenter], True
        )
        try:
            return (obj for obj in container.view if obj.name == name).next()
        except StopIteration:
            return None

    def renew_connection(self):
        self._create_connection()

    def create_event_history_collector(self, events_to_observe):
        event_manager = self._si.content.eventManager
        event_filter_spec = vim.event.EventFilterSpec()
        event_types = [getattr(vim.event, et) for et in events_to_observe]
        event_filter_spec.type = event_types
        entity_spec = vim.event.EventFilterSpec.ByEntity()
        entity_spec.entity = self._datacenter
        entity_spec.recursion = (
            vim.event.EventFilterSpec.RecursionOption.children
        )
        event_filter_spec.entity = entity_spec
        history_collector = event_manager.CreateCollectorForEvents(
            filter=event_filter_spec
        )
        history_collector.SetCollectorPageSize(
            const.HISTORY_COLLECTOR_PAGE_SIZE
        )
        return history_collector

    def add_filter(self, obj, filters):
        filter_spec = make_filter_spec(obj, filters)
        return self._property_collector.CreateFilter(filter_spec, True)

    def make_wait_options(
        self, max_wait_seconds=None, max_object_updates=None
    ):
        if max_object_updates is not None:
            self._wait_options.maxObjectUpdates = max_object_updates
        if max_wait_seconds is not None:
            self._wait_options.maxWaitSeconds = max_wait_seconds

    def wait_for_updates(self):
        update_set = self._property_collector.WaitForUpdatesEx(
            self._version, self._wait_options
        )
        if update_set:
            self._version = update_set.version
        return update_set

    def get_all_vms(self):
        return self._vm_view.view

    def get_vms_by_portgroup(self, portgroup_key):
        portgroup = self._get_dpg_by_key(portgroup_key)
        if portgroup is None:
            return []
        return portgroup.vm

    def get_all_portgroups(self):
        return self._pg_view.view

    def _get_dpg_by_key(self, key):
        all_dpgs = self.get_all_portgroups()
        try:
            return (dpg for dpg in all_dpgs if dpg.key == key).next()
        except StopIteration:
            return None

    def get_host(self, hostname):
        all_hosts = self.get_all_hosts()
        try:
            return (host for host in all_hosts if host.name == hostname).next()
        except StopIteration:
            return None

    def get_all_hosts(self):
        return self._host_view.view

    def is_vm_removed(self, vm_uuid, host_name):
        for _ in range(const.WAIT_FOR_VM_RETRY):
            vm = self._get_vm_by_uuid(vm_uuid)
            if vm is None:
                return True

            host = vm.runtime.host
            if host is None:
                logger.info(
                    "Host for VM %s is None. Waiting for update...", vm_uuid
                )
                time.sleep(1)
                continue

            if host_name != host.name:
                return False
            time.sleep(1)

        logger.error(
            "Unable to confirm that VM %s was removed or not...", vm_uuid
        )
        return False

    def _get_vm_by_uuid(self, vm_uuid):
        return self._si.content.searchIndex.FindByUuid(
            datacenter=self._datacenter,
            uuid=vm_uuid,
            vmSearch=True,
            instanceUuid=True,
        )


class VNCAPIClient(object):
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
        self.project_name = vnc_cfg.get("project_name", const.VNC_PROJECT_NAME)

    def get_project(self):
        try:
            return self.vnc_lib.project_read(
                ["default-domain", self.project_name]
            )

        except vnc_api.NoIdError:
            project = vnc_api.Project(name=self.project_name)
            project.set_id_perms(const.ID_PERMS)
            self.vnc_lib.project_create(project)

        return self.vnc_lib.project_read(["default-domain", self.project_name])

    def read_fabric(self, fabric_uuid):
        return self.vnc_lib.fabric_read(id=fabric_uuid)

    def create_vn(self, vnc_vn):
        try:
            self.vnc_lib.virtual_network_create(vnc_vn)
            logger.info("Created VN with name: %s in VNC", vnc_vn.name)
        except vnc_api.RefsExistError:
            logger.info("VN %s already exists in VNC", vnc_vn.name)

    def create_vpg(self, vnc_vpg):
        try:
            self.vnc_lib.virtual_port_group_create(vnc_vpg)
            logger.info("Created VPG with name: %s in VNC", vnc_vpg.name)
        except vnc_api.RefsExistError:
            logger.info("VPG %s already exists in VNC", vnc_vpg.name)

    def create_vmi(self, vnc_vmi):
        try:
            self.vnc_lib.virtual_machine_interface_create(vnc_vmi)
            logger.info("Created VMI with name: %s in VNC", vnc_vmi.name)
        except vnc_api.RefsExistError:
            logger.info("VMI %s already exists in VNC", vnc_vmi.name)

    def read_all_vns(self):
        vn_ref_list = self.vnc_lib.virtual_networks_list(
            parent_id=self.get_project().get_uuid()
        )["virtual-networks"]
        vns_in_vnc = [self.read_vn(vn_ref["uuid"]) for vn_ref in vn_ref_list]
        return [vn for vn in vns_in_vnc if has_proper_creator(vn)]

    def read_all_vpgs(self):
        vpg_ref_list = self.vnc_lib.virtual_port_groups_list()[
            "virtual-port-groups"
        ]
        vpgs_in_vnc = [
            self.read_vpg(vpg_ref["uuid"]) for vpg_ref in vpg_ref_list
        ]
        return [vpg for vpg in vpgs_in_vnc if has_proper_creator(vpg)]

    def read_all_vmis(self):
        vmi_ref_list = self.vnc_lib.virtual_machine_interfaces_list(
            parent_id=self.get_project().get_uuid()
        )["virtual-machine-interfaces"]
        vmis_in_vnc = [
            self.read_vmi(vmi_ref["uuid"]) for vmi_ref in vmi_ref_list
        ]
        return [vmi for vmi in vmis_in_vnc if has_proper_creator(vmi)]

    def read_vn(self, vn_uuid):
        try:
            return self.vnc_lib.virtual_network_read(id=vn_uuid)
        except vnc_api.NoIdError:
            logger.info("VN %s not found in VNC", vn_uuid)
        return None

    def read_vpg(self, vpg_uuid):
        try:
            return self.vnc_lib.virtual_port_group_read(id=vpg_uuid)
        except vnc_api.NoIdError:
            logger.info("VPG %s not found in VNC", vpg_uuid)
        return None

    def read_vmi(self, vmi_uuid):
        try:
            return self.vnc_lib.virtual_machine_interface_read(id=vmi_uuid)
        except vnc_api.NoIdError:
            logger.info("VMI %s not found in VNC", vmi_uuid)
        return None

    def update_vpg(self, vnc_vpg):
        try:
            self.vnc_lib.virtual_port_group_update(vnc_vpg)
            logger.info("Updated VPG with name: %s", vnc_vpg.name)
        except vnc_api.NoIdError:
            logger.info(
                "VPG %s not found in VNC, unable to update", vnc_vpg.uuid
            )

    def delete_vmi(self, vmi_uuid):
        self.detach_vmi_from_vpg(vmi_uuid)
        try:
            self.vnc_lib.virtual_machine_interface_delete(id=vmi_uuid)
            logger.info("VMI %s deleted from VNC", vmi_uuid)
        except vnc_api.NoIdError:
            logger.info("VMI %s not found in VNC, unable to delete", vmi_uuid)

    def delete_vpg(self, vpg_uuid):
        try:
            self.vnc_lib.virtual_port_group_delete(id=vpg_uuid)
            logger.info("VPG %s deleted from VNC", vpg_uuid)
        except vnc_api.NoIdError:
            logger.info("VPG %s not found in VNC, unable to delete", vpg_uuid)

    def delete_vn(self, vn_uuid):
        vnc_vn = self.read_vn(vn_uuid)
        for vnc_vmi in self.get_vmis_by_vn(vnc_vn):
            self.delete_vmi(vnc_vmi.uuid)
        try:
            self.vnc_lib.virtual_network_delete(id=vn_uuid)
            logger.info("VN %s deleted from VNC", vn_uuid)
        except vnc_api.NoIdError:
            logger.info("VN %s not found in VNC, unable to delete", vn_uuid)

    def _read_physical_router(self, pr_uuid):
        try:
            return self.vnc_lib.physical_router_read(id=pr_uuid)
        except vnc_api.RefsExistError:
            logger.info("Physical router %s not found in VNC", pr_uuid)

    def read_all_physical_routers(self):
        pr_refs = self.vnc_lib.physical_routers_list()["physical-routers"]
        return [
            self._read_physical_router(pr_ref["uuid"]) for pr_ref in pr_refs
        ]

    def _read_node(self, node_uuid):
        try:
            return self.vnc_lib.node_read(id=node_uuid)
        except vnc_api.NoIdError:
            logger.info("Node %s not found in VNC", node_uuid)

    def _read_all_nodes(self):
        node_refs = self.vnc_lib.nodes_list()["nodes"]
        return [self._read_node(node_ref["uuid"]) for node_ref in node_refs]

    def get_nodes_by_host_names(self, esxi_names):
        vnc_nodes = self._read_all_nodes()
        return [
            vnc_node for vnc_node in vnc_nodes if vnc_node.name in esxi_names
        ]

    def get_node_ports(self, node):
        port_refs = node.get_ports()
        return [self._read_port(port_ref["uuid"]) for port_ref in port_refs]

    def read_all_ports(self):
        port_refs = self.vnc_lib.ports_list()["ports"]
        return [self._read_port(port_ref["uuid"]) for port_ref in port_refs]

    def _read_port(self, port_uuid):
        return self.vnc_lib.port_read(id=port_uuid)

    def read_pi(self, pi_uuid):
        try:
            return self.vnc_lib.physical_interface_read(id=pi_uuid)
        except vnc_api.NoIdError:
            logger.info("Physical Interface %s not found in VNC", pi_uuid)

    def get_pis_by_port(self, port):
        pi_refs = port.get_physical_interface_back_refs()
        return [self.read_pi(pi_ref["uuid"]) for pi_ref in pi_refs]

    def attach_pis_to_vpg(self, vpg, physical_interfaces):
        if not physical_interfaces:
            return
        for pi in physical_interfaces:
            vpg.add_physical_interface(pi)
            pi_display_name = ":".join(pi.fq_name[1:])
            logger.info(
                "Attached physical interface %s to VPG %s",
                pi_display_name,
                vpg.name,
            )
        self.vnc_lib.virtual_port_group_update(vpg)

    def detach_pis_from_vpg(self, vpg, physical_interface_uuids):
        if not physical_interface_uuids:
            return
        for pi_uuid in physical_interface_uuids:
            pi = self.read_pi(pi_uuid)
            vpg.del_physical_interface(pi)
            pi_display_name = ":".join(pi.fq_name[1:])
            logger.info(
                "Detached physical interface %s from VPG %s",
                pi_display_name,
                vpg.name,
            )
        self.vnc_lib.virtual_port_group_update(vpg)

    def detach_vmi_from_vpg(self, vmi_uuid):
        vmi = self.read_vmi(vmi_uuid)
        if vmi is None:
            return
        vpg_refs = vmi.get_virtual_port_group_back_refs()
        if vpg_refs is None:
            return
        vpg_ref = vpg_refs[0]
        vpg = self.read_vpg(vpg_ref["uuid"])
        vpg.del_virtual_machine_interface(vmi)
        self.update_vpg(vpg)
        logger.info("VMI %s detached from VPG %s", vmi.name, vpg.name)
        if not vpg.get_virtual_machine_interface_refs():
            self.delete_vpg(vpg.uuid)

    def get_vn_vlan(self, vnc_vn):
        vmi_refs = vnc_vn.get_virtual_machine_interface_back_refs() or ()
        if len(vmi_refs) == 0:
            return None
        vmi_ref = vmi_refs[0]
        vmi_uuid = vmi_ref["uuid"]
        vnc_vmi = self.read_vmi(vmi_uuid)
        vmi_properties = vnc_vmi.get_virtual_machine_interface_properties()
        return vmi_properties.get_sub_interface_vlan_tag()

    def get_vmis_by_vn(self, vnc_vn):
        vmi_refs = vnc_vn.get_virtual_machine_interface_back_refs() or ()
        return [self.read_vmi(vmi_ref["uuid"]) for vmi_ref in vmi_refs]

    def recreate_vmi_with_new_vlan(self, old_vnc_vmi, vnc_vn, new_vlan):
        logger.info(
            "Recreating VMI %s with new vlan %s in VNC",
            old_vnc_vmi.name,
            new_vlan,
        )
        vpg_ref = old_vnc_vmi.get_virtual_port_group_back_refs()[0]
        vnc_vpg = self.read_vpg(vpg_ref["uuid"])
        new_vnc_vmi = self._create_vnc_vmi_obj_with_new_vlan(
            new_vlan, old_vnc_vmi, vnc_vn
        )
        self._delete_old_vmi(old_vnc_vmi, vnc_vpg)
        self._create_new_vmi(new_vnc_vmi, vnc_vpg)
        logger.info(
            "Recreated VMI %s with new vlan %s in VNC",
            old_vnc_vmi.name,
            new_vlan,
        )

    def _create_vnc_vmi_obj_with_new_vlan(self, new_vlan, old_vnc_vmi, vnc_vn):
        new_vnc_vmi = vnc_api.VirtualMachineInterface(
            name=old_vnc_vmi.name, parent_obj=self.get_project()
        )
        new_vnc_vmi.set_uuid(old_vnc_vmi.uuid)
        new_vnc_vmi.add_virtual_network(vnc_vn)
        vmi_properties = vnc_api.VirtualMachineInterfacePropertiesType(
            sub_interface_vlan_tag=new_vlan
        )
        new_vnc_vmi.set_virtual_machine_interface_properties(vmi_properties)
        new_vnc_vmi.set_id_perms(const.ID_PERMS)
        return new_vnc_vmi

    def _delete_old_vmi(self, vnc_vmi, vnc_vpg):
        vnc_vpg.del_virtual_machine_interface(vnc_vmi)
        logger.info("Detached VMI %s from VPG %s", vnc_vmi.name, vnc_vpg.name)
        self.update_vpg(vnc_vpg)
        self.vnc_lib.virtual_machine_interface_delete(id=vnc_vmi.uuid)
        logger.info("Deleted VMI %s from VNC", vnc_vmi.name)

    def _create_new_vmi(self, new_vnc_vmi, vnc_vpg):
        self.create_vmi(new_vnc_vmi)
        vnc_vpg.add_virtual_machine_interface(new_vnc_vmi)
        logger.info(
            "Attached VMI %s from VPG %s", new_vnc_vmi.name, vnc_vpg.name
        )
        self.update_vpg(vnc_vpg)
