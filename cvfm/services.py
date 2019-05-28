import logging

from cvfm import constants as const
from cvfm import models
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

    def get_host_model(self, host_name):
        logger.info("VirtualMachineService.get_host_model called")

    def create_vm_model(self, vmware_vm):
        vm_model = models.VirtualMachineModel.from_vmware_vm(vmware_vm)
        self._database.add_vm_model(vm_model)
        return vm_model

    def delete_vm_model(self, vm_name):
        vm_model = self._database.get_vm_model(vm_name)
        self._database.remove_vm_model(vm_name)
        return vm_model

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
        return old_vmi_models - new_vmi_models

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

    def detect_vlan_change(self, vmware_dpg):
        logger.info("DistributedPortGroupService.detect_vlan_change called")
        return True

    def handle_vlan_change(self, vmware_dpg):
        logger.info("DistributedPortGroupService.handle_vlan_change called")

    def rename_dpg(self, dpg_uuid, new_dpg_name):
        logger.info("DistributedPortGroupService.rename_dpg called")

    def delete_dpg_model(self, dpg_name):
        logger.info("DistributedPortGroupService.delete_dpg_model called")

    def delete_fabric_vn(self, dpg_model):
        logger.info("DistributedPortGroupService.delete_fabric_vn called")

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
            vnc_vpg = vpg_model.to_vnc_vpg()
            self._vnc_api_client.create_vpg(vnc_vpg)

    def attach_pis_to_vpg(self, vpg_model):
        vnc_vpg = self._vnc_api_client.read_vpg(vpg_model.uuid)
        pis = self.find_matches_physical_interfaces(
            vpg_model.host_name, vpg_model.dvs_name
        )
        self._vnc_api_client.connect_physical_interfaces_to_vpg(vnc_vpg, pis)

    def find_matches_physical_interfaces(self, host_name, dvs_name):
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
            if self.is_dvs_in_port_annotations(port, dvs_name)
        ]

    def is_dvs_in_port_annotations(self, port, dvs_name):
        annotations = port.get_annotations().key_value_pair
        for annotation in annotations:
            if (
                annotation.value == const.DVS_ANNOTATION
                and annotation.key == dvs_name
            ):
                return True
        return False

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
