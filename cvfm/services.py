import logging

from pyVmomi import vim

from cvfm import models, exceptions, constants
from cvfm.exceptions import (
    VNCVMICreationException,
    DPGCreationException,
    VNCPortValidationException,
)

logger = logging.getLogger(__name__)


class Service(object):
    def __init__(self, vcenter_api_client, vnc_api_client, database):
        self._vcenter_api_client = vcenter_api_client
        self._vnc_api_client = vnc_api_client
        self._database = database


class VirtualMachineService(Service):
    def populate_db_with_vms(self):
        vmware_vms = self._vcenter_api_client.get_all_vms()
        for vmware_vm in vmware_vms:
            try:
                self.create_vm_model(vmware_vm)
            except Exception:
                logger.exception("Unexpected error during VM model creation")

    def create_vm_model(self, vmware_vm):
        dpg_models = set()
        for net in vmware_vm.network:
            dpg_model = self._database.get_dpg_model(net.name)
            if dpg_model:
                dpg_models.add(dpg_model)

        vm_model = models.VirtualMachineModel.from_vmware_vm(
            vmware_vm, dpg_models
        )
        self._database.add_vm_model(vm_model)
        property_filter = self._vcenter_api_client.add_filter(
            vmware_vm, constants.VM_UPDATE_FILTERS
        )
        vm_model.set_property_filter(property_filter)
        return vm_model

    def delete_vm_model(self, vm_name):
        vm_model = self._database.get_vm_model(vm_name)
        self._database.remove_vm_model(vm_name)
        if vm_model is not None:
            vm_model.destroy_property_filter()
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

    def rename_vm_model(self, old_name, new_name):
        vm_model = self._database.remove_vm_model(old_name)
        if vm_model is None:
            logger.error(
                "VM model %s could not be found in Database", old_name
            )
            return
        vm_model.name = new_name
        self._database.add_vm_model(vm_model)
        logger.info("VM model renamed from %s to %s", old_name, new_name)

    def check_vm_moved(self, vm_name, host):
        vm_model = self._database.get_vm_model(vm_name)
        if vm_model is None:
            return False
        return vm_model.host_name != host.name

    def get_host_from_vm(self, vm_name):
        vm_model = self._database.get_vm_model(vm_name)
        return self._vcenter_api_client.get_host(vm_model.host_name)

    def is_vm_removed_from_vcenter(self, vm_name, host_name):
        return self._vcenter_api_client.is_vm_removed(vm_name, host_name)


class VirtualMachineInterfaceService(Service):
    def create_vmi_models_for_vm(self, vm_model):
        return models.VirtualMachineInterfaceModel.from_vm_model(vm_model)

    def create_vmi_in_vnc(self, vmi_model):
        fabric_vn = self._vnc_api_client.read_vn(vmi_model.dpg_model.uuid)
        project = self._vnc_api_client.get_project()
        try:
            vnc_vmi = vmi_model.to_vnc_vmi(project, fabric_vn)
        except VNCVMICreationException as exc:
            logger.error(
                "Unable to create VMI in VNC for %s. Reason: %s",
                vmi_model,
                exc,
            )
            return
        existing_vmi = self._vnc_api_client.read_vmi(vmi_model.uuid)
        if existing_vmi is None:
            self._vnc_api_client.create_vmi(vnc_vmi)
        else:
            self._update_existing_vmi(vmi_model, existing_vmi, fabric_vn)

    def _update_existing_vmi(self, vmi_model, existing_vmi, fabric_vn):
        old_props = existing_vmi.get_virtual_machine_interface_properties()
        old_vlan = old_props.get_sub_interface_vlan_tag()
        new_vlan = vmi_model.dpg_model.vlan_id
        if old_vlan != new_vlan:
            logger.info(
                "Detected VLAN change for VMI %s from VLAN %s to VLAN %s",
                vmi_model.name,
                old_vlan,
                new_vlan,
            )
            self._vnc_api_client.recreate_vmi_with_new_vlan(
                existing_vmi, fabric_vn, new_vlan
            )

    def attach_vmi_to_vpg(self, vmi_model):
        vnc_vmi = self._vnc_api_client.read_vmi(vmi_model.uuid)
        if vnc_vmi is None:
            return
        vnc_vpg = self._vnc_api_client.read_vpg(vmi_model.vpg_uuid)
        vmi_refs = vnc_vpg.get_virtual_machine_interface_refs() or ()
        vmi_uuids = [vmi_ref["uuid"] for vmi_ref in vmi_refs]
        if vnc_vmi.uuid not in vmi_uuids:
            vnc_vpg.add_virtual_machine_interface(vnc_vmi)
            logger.info(
                "Attached VMI %s to VPG %s", vnc_vmi.name, vnc_vpg.name
            )
            self._vnc_api_client.update_vpg(vnc_vpg)

    def find_affected_vmis(self, old_vm_model, new_vm_model):
        if old_vm_model is None:
            old_vmi_models = set()
        else:
            old_vmi_models = set(self.create_vmi_models_for_vm(old_vm_model))
        new_vmi_models = set(self.create_vmi_models_for_vm(new_vm_model))
        vmis_to_delete = old_vmi_models - new_vmi_models
        vmis_to_create = new_vmi_models - old_vmi_models
        return vmis_to_delete, vmis_to_create

    def delete_vmi(self, vmi_uuid):
        self._vnc_api_client.delete_vmi(vmi_uuid)

    def read_all_vmis(self):
        return self._vnc_api_client.read_all_vmis()


class DistributedPortGroupService(Service):
    def populate_db_with_dpgs(self):
        for vmware_dpg in self._vcenter_api_client.get_all_portgroups():
            try:
                self.create_dpg_model(vmware_dpg)
            except exceptions.DPGCreationException as exc:
                logger.info(
                    "Unable to create DPG model for %s portgroup, Reason: %s",
                    vmware_dpg.name,
                    exc,
                )
            except Exception:
                logger.exception("Unexpected error during DPG model creation")

    def create_dpg_model(self, vmware_dpg):
        self._validate_dpg(vmware_dpg)
        dpg_model = models.DistributedPortGroupModel.from_vmware_dpg(
            vmware_dpg
        )
        self._database.add_dpg_model(dpg_model)
        return dpg_model

    def create_fabric_vn(self, dpg_model):
        project = self._vnc_api_client.get_project()
        vnc_vn = dpg_model.to_vnc_vn(project)
        self._vnc_api_client.create_vn(vnc_vn)
        logger.info("Virtual Network %s created in VNC", vnc_vn.name)

    def get_all_dpg_models(self):
        return self._database.get_all_dpg_models()

    def get_all_fabric_vns(self):
        return self._vnc_api_client.read_all_vns()

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
                dpg_model.name,
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
            self._vnc_api_client.recreate_vmi_with_new_vlan(
                vnc_vmi, vnc_vn, dpg_model.vlan_id
            )

    def rename_dpg(self, old_dpg_name, new_dpg_name):
        dpg_model = self._database.get_dpg_model(old_dpg_name)
        dpg_model.name = new_dpg_name
        self._database.remove_dpg_model(old_dpg_name)
        self._database.add_dpg_model(dpg_model)
        logger.info(
            "DPG model renamed from %s to %s", old_dpg_name, new_dpg_name
        )

    def delete_dpg_model(self, dpg_name):
        for vm_model in self._database.get_all_vm_models():
            vm_model.detach_dpg(dpg_name)
        dpg_model = self._database.remove_dpg_model(dpg_name)
        logger.info("DPG model %s deleted", dpg_name)
        return dpg_model

    def delete_fabric_vn(self, dpg_uuid):
        self._vnc_api_client.delete_vn(dpg_uuid)

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
        is_empty = vms_in_pg_and_on_host == set()
        if is_empty:
            logger.info(
                "DPG with key %s is empty on host: %s",
                portgroup_key,
                host.name,
            )
        else:
            logger.info(
                "DPG with key %s is not empty on host: %s",
                portgroup_key,
                host.name,
            )
        return is_empty

    def _validate_dpg(self, vmware_dpg):
        self._validate_vlan_id(vmware_dpg)
        self._validate_type(vmware_dpg)
        self._validate_dvs(vmware_dpg)

    def _validate_dvs(self, vmware_dpg):
        dvs_name = vmware_dpg.config.distributedVirtualSwitch.name
        if not self._database.is_dvs_supported(dvs_name):
            raise DPGCreationException(
                "DVS {} is not supported.".format(dvs_name)
            )

    @staticmethod
    def _validate_vlan_id(vmware_dpg):
        try:
            vlan_id = int(vmware_dpg.config.defaultPortConfig.vlan.vlanId)
        except (TypeError, AttributeError):
            raise DPGCreationException("VLAN ID must be a number.")
        if vlan_id == 0:
            raise DPGCreationException("VLAN ID cannot be 0.")

    @staticmethod
    def _validate_type(vmware_dpg):
        if not isinstance(vmware_dpg, vim.DistributedVirtualPortgroup):
            raise DPGCreationException(
                "{} is not a Distributed Portgroup".format(vmware_dpg.name)
            )


class VirtualPortGroupService(Service):
    def create_vpg_models(self, vm_model):
        return models.VirtualPortGroupModel.from_vm_model(vm_model)

    def create_vpg_in_vnc(self, vpg_model, pi_models):
        if not pi_models:
            return
        vnc_pis = [
            self._vnc_api_client.read_pi(pi_model.uuid)
            for pi_model in pi_models
        ]
        vnc_vpg = self._vnc_api_client.read_vpg(vpg_model.uuid)
        if vnc_vpg is None:
            logger.info("Not found VPG in VNC for %s. Creating...", vpg_model)
            vnc_vpg = self._create_vpg(vpg_model)

        self.update_pis_for_vpg(vnc_vpg, vnc_pis)

    def _create_vpg(self, vpg_model):
        fabric = self._vnc_api_client.get_fabric()
        vnc_vpg = vpg_model.to_vnc_vpg(fabric)
        self._vnc_api_client.create_vpg(vnc_vpg)
        return vnc_vpg

    def read_all_vpgs(self):
        return self._vnc_api_client.read_all_vpgs()

    def delete_vpg(self, vpg_uuid):
        self._vnc_api_client.delete_vpg(vpg_uuid)

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
        pis_change = len(pis_to_attach) != 0 or len(pis_to_attach) != 0
        if not pis_change:
            return
        logger.info(
            "Updating list of physical interfaces connected to VPG %s",
            existing_vpg.name,
        )
        self._vnc_api_client.attach_pis_to_vpg(existing_vpg, pis_to_attach)
        self._vnc_api_client.detach_pis_from_vpg(existing_vpg, pis_to_detach)
        logger.info(
            "Updated list of physical interfaces connected to VPG %s",
            existing_vpg.name,
        )


class DistributedVirtualSwitchService(Service):
    def populate_db_with_supported_dvses(self):
        ports = self._vnc_api_client.read_all_ports()
        for port in ports:
            esxi_props = port.get_esxi_port_info()
            if not esxi_props:
                continue
            dvs_name = esxi_props.get_dvs_name()
            if dvs_name:
                self._database.add_supported_dvs(dvs_name)
                logger.debug("DVS %s added as a supported DVS", dvs_name)


def validate_vnc_port(vnc_port):
    esxi_port_info = vnc_port.get_esxi_port_info()
    if not esxi_port_info:
        raise VNCPortValidationException(
            "No ESXi info could be read from port %s", vnc_port.name
        )
    dvs_name = esxi_port_info.get_dvs_name()
    if not dvs_name:
        raise VNCPortValidationException(
            "No DVS name could be read from port %s", vnc_port.name
        )


class PhysicalInterfaceService(Service):
    def get_pi_models_for_vpg(self, vpg_model):
        return self._database.get_pi_models_for_vpg(vpg_model)

    def populate_db_with_pi_models(self):
        vnc_nodes = self._get_vnc_nodes()
        for vnc_node in vnc_nodes:
            self._create_pis_for_node(vnc_node)

    def _get_vnc_nodes(self):
        host_names_in_vcenter = [
            host.name for host in self._vcenter_api_client.get_all_hosts()
        ]
        vnc_nodes = self._vnc_api_client.get_nodes_by_host_names(
            host_names_in_vcenter
        )
        return vnc_nodes

    def _create_pis_for_node(self, vnc_node):
        node_ports = self._vnc_api_client.get_node_ports(vnc_node)
        for vnc_port in node_ports:
            try:
                self._create_pis_for_port(vnc_node, vnc_port)
            except VNCPortValidationException:
                continue

    def _create_pis_for_port(self, vnc_node, vnc_port):
        validate_vnc_port(vnc_port)
        host_name = vnc_node.name
        dvs_name = vnc_port.get_esxi_port_info().get_dvs_name()
        vnc_pis = self._vnc_api_client.get_pis_by_port(vnc_port)
        self._create_pi_models_in_db(vnc_pis, host_name, dvs_name)

    def _create_pi_models_in_db(self, vnc_pis, host_name, dvs_name):
        pi_models = [
            models.PhysicalInterfaceModel(pi.uuid, host_name, dvs_name)
            for pi in vnc_pis
        ]
        for pi_model in pi_models:
            self._database.add_pi_model(pi_model)
            logger.debug("Physical Interface %s added", pi_model)
