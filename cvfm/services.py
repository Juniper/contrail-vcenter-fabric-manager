import logging

from cvfm import models, exceptions
from cvfm.exceptions import VNCVMICreationException

logger = logging.getLogger(__name__)


class Service(object):
    def __init__(self, vcenter_api_client, vnc_api_client, database):
        self._vcenter_api_client = vcenter_api_client
        self._vnc_api_client = vnc_api_client
        self._database = database


class VirtualMachineService(Service):
    def __init__(self, vcenter_api_client, vnc_api_client, database):
        super(VirtualMachineService, self).__init__(
            vcenter_api_client, vnc_api_client, database
        )

    def populate_db_with_vms(self):
        vmware_vms = self._vcenter_api_client.get_all_vms()
        for vmware_vm in vmware_vms:
            self.create_vm_model(vmware_vm)

    def create_vm_model(self, vmware_vm):
        vm_model = models.VirtualMachineModel.from_vmware_vm(vmware_vm)
        self._database.add_vm_model(vm_model)
        return vm_model

    def delete_vm_model(self, vm_name):
        vm_model = self._database.get_vm_model(vm_name)
        self._database.remove_vm_model(vm_name)
        return vm_model

    def update_dpg_in_vm_models(self, dpg_model):
        for vm_model in self._database.get_all_vm_models():
            if vm_model.has_interface_in_dpg(dpg_model):
                vm_model.detach_dpg(dpg_model.name)
                vm_model.attach_dpg(dpg_model)

    def get_all_vm_models(self):
        return self._database.get_all_vm_models()

    def create_vm_models_for_dpg_model(self, dpg_model):
        vm_models = []
        for vmware_vm in self._vcenter_api_client.get_vms_by_portgroup(
            dpg_model.key
        ):
            vm_model = self.create_vm_model(vmware_vm)
            vm_models.append(vm_model)
        return vm_models

    def migrate_vm_model(self, vm_uuid, target_host_model):
        logger.info("VirtualMachineService.migrate_vm_model called")
        return models.VirtualMachineModel()

    def rename_vm_model(self, vm_uuid, new_name):
        logger.info("VirtualMachineService.rename_vm_model called")


class VirtualMachineInterfaceService(Service):
    def __init__(self, vcenter_api_client, vnc_api_client, database):
        super(VirtualMachineInterfaceService, self).__init__(
            vcenter_api_client, vnc_api_client, database
        )

    def create_vmi_models_for_vm(self, vm_model):
        return models.VirtualMachineInterfaceModel.from_vm_model(vm_model)

    def create_vmi_in_vnc(self, vmi_model):
        if self._vnc_api_client.read_vmi(vmi_model.uuid) is None:
            project = self._vnc_api_client.get_project()
            fabric_vn = self._vnc_api_client.read_vn(vmi_model.dpg_model.uuid)
            try:
                vnc_vmi = vmi_model.to_vnc_vmi(project, fabric_vn)
            except VNCVMICreationException:
                return
            self._vnc_api_client.create_vmi(vnc_vmi)

    def attach_vmi_to_vpg(self, vmi_model):
        vnc_vmi = self._vnc_api_client.read_vmi(vmi_model.uuid)
        if vnc_vmi is None:
            return
        vnc_vpg = self._vnc_api_client.read_vpg(vmi_model.vpg_uuid)
        vnc_vpg.add_virtual_machine_interface(vnc_vmi)
        self._vnc_api_client.update_vpg(vnc_vpg)

    def detach_vmi_from_vpg(self, vmi_model):
        vnc_vpg = self._vnc_api_client.read_vpg(vmi_model.vpg_uuid)
        vnc_vmi = self._vnc_api_client.read_vmi(vmi_model.uuid)
        vnc_vpg.del_virtual_machine_interface(vnc_vmi)
        self._vnc_api_client.update_vpg(vnc_vpg)
        logger.info("VMI %s detached from VPG %s", vnc_vmi.name, vnc_vpg.name)

    def find_affected_vmis(self, old_vm_model, new_vm_model):
        old_vmi_models = set(self.create_vmi_models_for_vm(old_vm_model))
        new_vmi_models = set(self.create_vmi_models_for_vm(new_vm_model))
        vmis_to_delete = old_vmi_models - new_vmi_models
        vmis_to_create = new_vmi_models - old_vmi_models
        return vmis_to_delete, vmis_to_create

    def delete_vmi(self, vmi_model):
        self._vnc_api_client.delete_vmi(vmi_model.uuid)

    def add_vmi(self, vm_uuid, vmware_vmi):
        logger.info("VirtualMachineInterfaceService.add_vmi called")

    def migrate_vmi(self, vmi_model, source_host_model, target_host_model):
        logger.info("VirtualMachineInterfaceService.migrate_vmi called")


class DistributedPortGroupService(Service):
    def __init__(self, vcenter_api_client, vnc_api_client, database):
        super(DistributedPortGroupService, self).__init__(
            vcenter_api_client, vnc_api_client, database
        )

    def create_dpg_model(self, vmware_dpg):
        return models.DistributedPortGroupModel.from_vmware_dpg(vmware_dpg)

    def create_fabric_vn(self, dpg_model):
        project = self._vnc_api_client.get_project()
        vnc_vn = dpg_model.to_vnc_vn(project)

        self._vnc_api_client.create_vn(vnc_vn)
        logger.info("Virtual Network %s created in VNC", vnc_vn.name)

    def get_all_dpg_models(self):
        dpg_models = []
        for vmware_dpg in self._vcenter_api_client.get_all_portgroups():
            try:
                dpg_models.append(self.create_dpg_model(vmware_dpg))
            except exceptions.DPGCreationException:
                logger.exception(
                    "Error while creating a model for DPG: %s", vmware_dpg.name
                )
        return dpg_models

    def get_all_fabric_vn_uuids(self):
        return self._vnc_api_client.read_all_vn_uuids()

    def exists_vn_for_portgroup(self, vmware_dpg_key):
        vn_uuid = models.generate_uuid(vmware_dpg_key)
        vnc_vn = self._vnc_api_client.read_vn(vn_uuid)
        return vnc_vn is not None

    def should_update_vlan(self, dpg_model):
        vnc_vn = self._vnc_api_client.read_vn(dpg_model.uuid)
        vnc_vlan = self._vnc_api_client.get_vn_vlan(vnc_vn)
        if vnc_vlan is None:
            return False
        should_update = vnc_vlan != dpg_model.vlan_id
        if should_update:
            logger.info(
                "Detected VLAN change for %s from %s to %s",
                dpg_model,
                vnc_vlan,
                dpg_model.vlan_id,
            )
        else:
            logger.info("No VLAN change for %s", dpg_model)
        return should_update

    def update_vmis_vlan_in_vnc(self, dpg_model):
        vnc_vn = self._vnc_api_client.read_vn(dpg_model.uuid)
        vnc_vmis = self._vnc_api_client.get_vmis_by_vn(vnc_vn)
        for vnc_vmi in vnc_vmis:
            logger.info(
                "Recreating VMI %s with new VLAN %s in VNC...",
                vnc_vmi.name,
                dpg_model.vlan_id,
            )
            self._vnc_api_client.recreate_vmi_with_new_vlan(
                vnc_vmi, vnc_vn, dpg_model.vlan_id
            )
            logger.info(
                "Recreated VMI %s with new VLAN %s in VNC",
                vnc_vmi.name,
                dpg_model.vlan_id,
            )

    def create_fabric_vmi_for_vm_vmi(self, vmi_model):
        logger.info(
            "DistributedPortGroupService.create_fabric_vmi_for_vm_vmi called"
        )

    def delete_fabric_vmi_for_vm_vmi(self, vmi_model):
        logger.info(
            "DistributedPortGroupService.delete_fabric_vmi_for_vm_vmi called"
        )

    def handle_vm_vmi_migration(self, vmi_model, source_host_model):
        logger.info(
            "DistributedPortGroupService.handle_vm_vmi_migration called"
        )

    def get_dvs_model(self, vmware_dvs):
        logger.info("DistributedPortGroupService.get_dvs_model called")

    def rename_dpg(self, dpg_uuid, new_dpg_name):
        logger.info("DistributedPortGroupService.rename_dpg called")

    def delete_dpg_model(self, dpg_name):
        for vm_model in self._database.get_all_vm_models():
            vm_model.detach_dpg(dpg_name)

        logger.info("DPG model %s deleted", dpg_name)

    def delete_fabric_vn(self, dvs_name, dpg_name):
        project = self._vnc_api_client.get_project()
        dpg_vnc_name = models.DistributedPortGroupModel.get_vnc_name(
            dvs_name, dpg_name
        )
        dpg_fq_name = project.fq_name + [dpg_vnc_name]

        self._vnc_api_client.delete_vn(dpg_fq_name)

    def clean_fabric_vn(self, dvs_name, dpg_name):
        project = self._vnc_api_client.get_project()
        dpg_vnc_name = models.DistributedPortGroupModel.get_vnc_name(
            dvs_name, dpg_name
        )
        dpg_fq_name = project.fq_name + [dpg_vnc_name]
        dpg_vn = self._vnc_api_client.read_vn_by_fq_name(dpg_fq_name)

        affected_vpgs = set()
        vmis = self._vnc_api_client.get_vmis_by_vn(dpg_vn)
        for vmi in vmis:
            for vpg_ref in vmi.get_virtual_port_group_back_refs():
                affected_vpgs.add(vpg_ref["uuid"])
                self._vnc_api_client.detach_vmi_from_vpg(vmi, vpg_ref["uuid"])
            self._vnc_api_client.delete_vmi(vmi.uuid)
        return affected_vpgs

    def filter_out_non_empty_dpgs(self, vmi_models, host):
        return [
            vmi_model
            for vmi_model in vmi_models
            if self.is_pg_empty_on_host(vmi_model.dpg_model.key, host)
        ]

    def is_pg_empty_on_host(self, portgroup_key, host):
        vms_in_pg = set(
            self._vcenter_api_client.get_vms_by_portgroup(portgroup_key)
        )
        vms_on_host = set(host.vm)
        vms_in_pg_and_on_host = vms_in_pg.intersection(vms_on_host)
        return vms_in_pg_and_on_host == set()


class VirtualPortGroupService(Service):
    def __init__(self, vcenter_api_client, vnc_api_client, database):
        super(VirtualPortGroupService, self).__init__(
            vcenter_api_client, vnc_api_client, database
        )

    def create_vpg_models(self, vm_model):
        return models.VirtualPortGroupModel.from_vm_model(vm_model)

    def create_vpg_in_vnc(self, vpg_model):
        if self._vnc_api_client.read_vpg(vpg_model.uuid) is None:
            fabric = self._vnc_api_client.get_fabric()
            vnc_vpg = vpg_model.to_vnc_vpg(fabric)
            self._vnc_api_client.create_vpg(vnc_vpg)

    def attach_pis_to_vpg(self, vpg_model):
        vnc_vpg = self._vnc_api_client.read_vpg(vpg_model.uuid)
        pis = self.find_matching_physical_interfaces(
            vpg_model.host_name, vpg_model.dvs_name
        )
        self.update_pis_for_vpg(vnc_vpg, pis)

    def update_pis_for_vpg(self, existing_vpg, pis):
        previous_pis_uuids = [
            pi_ref["uuid"]
            for pi_ref in existing_vpg.get_physical_interface_refs() or ()
        ]
        pis_to_attach = [pi for pi in pis if pi.uuid not in previous_pis_uuids]

        current_pis_uuids = [pi.uuid for pi in pis]
        pis_to_detach = [
            pi_uuid
            for pi_uuid in previous_pis_uuids
            if pi_uuid not in current_pis_uuids
        ]

        self._vnc_api_client.attach_pis_to_vpg(existing_vpg, pis_to_attach)
        self._vnc_api_client.detach_pis_from_vpg(existing_vpg, pis_to_detach)

    def find_matching_physical_interfaces(self, host_name, dvs_name):
        vnc_node = self._vnc_api_client.get_node_by_name(host_name)
        if vnc_node is None:
            return []
        vnc_ports = self._vnc_api_client.get_node_ports(vnc_node)
        vnc_ports = self.filter_node_ports_by_dvs_name(vnc_ports, dvs_name)
        return self.collect_pis_from_ports(vnc_ports)

    def collect_pis_from_ports(self, vnc_ports):
        pis = []
        for port in vnc_ports:
            port_pis = self._vnc_api_client.get_pis_by_port(port)
            pis.extend(port_pis)
        return pis

    def filter_node_ports_by_dvs_name(self, ports, dvs_name):
        return [
            port
            for port in ports
            if self.is_dvs_name_in_port_info(port, dvs_name)
        ]

    @staticmethod
    def is_dvs_name_in_port_info(port, dvs_name):
        esxi_port_info = port.get_esxi_port_info()
        if esxi_port_info is None:
            return False
        return esxi_port_info.get_dvs_name() == dvs_name

    def find_affected_vpgs(self, vmi_models):
        affected_vpgs = set()
        for vmi_model in vmi_models:
            vnc_vmi = self._vnc_api_client.read_vmi(vmi_model.uuid)
            vpg_back_refs = vnc_vmi.get_virtual_port_group_back_refs() or []
            affected_vpgs.update(ref["uuid"] for ref in vpg_back_refs)
        return affected_vpgs

    def prune_empty_vpgs(self, vpg_uuids):
        for vpg_uuid in vpg_uuids:
            vnc_vpg = self._vnc_api_client.read_vpg(vpg_uuid)
            if vnc_vpg.get_virtual_machine_interface_refs() is None:
                logger.info(
                    "VPG %s has no VMIs attached. Deleting...", vnc_vpg.name
                )
                self._vnc_api_client.delete_vpg(vpg_uuid)
