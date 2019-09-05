import logging

from cvfm import exceptions, models
from cvfm.services.base import Service
from pyVmomi import vim

__all__ = ["DistributedPortGroupService"]


logger = logging.getLogger(__name__)


class DistributedPortGroupService(Service):
    def populate_db_with_dpgs(self):
        for vmware_dpg in self._vcenter_api_client.get_all_portgroups():
            try:
                self.create_dpg_model(vmware_dpg)
            except exceptions.DPGCreationError as exc:
                logger.info(
                    "Unable to create DPG model for %s portgroup, Reason: %s",
                    vmware_dpg.name,
                    exc,
                )
            except exceptions.ConnectionLostError:
                raise
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
        self._validate_type(vmware_dpg)
        self._validate_vlan_id(vmware_dpg)
        self._validate_dvs(vmware_dpg)

    def _validate_dvs(self, vmware_dpg):
        dvs_name = vmware_dpg.config.distributedVirtualSwitch.name
        if not self._database.is_dvs_supported(dvs_name):
            raise exceptions.DPGCreationError(
                "DVS {} is not " "supported.".format(dvs_name)
            )

    @staticmethod
    def _validate_vlan_id(vmware_dpg):
        try:
            vlan_id = int(vmware_dpg.config.defaultPortConfig.vlan.vlanId)
        except (TypeError, AttributeError):
            raise exceptions.DPGCreationError("VLAN ID must be a number.")
        if vlan_id == 0:
            raise exceptions.DPGCreationError("VLAN ID cannot be 0.")

    @staticmethod
    def _validate_type(vmware_dpg):
        if not isinstance(vmware_dpg, vim.DistributedVirtualPortgroup):
            raise exceptions.DPGCreationError(
                "{} is not a Distributed Portgroup".format(vmware_dpg.name)
            )
