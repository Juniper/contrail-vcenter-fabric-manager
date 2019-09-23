from builtins import str
from builtins import object
import logging
import uuid as uid

from vnc_api import vnc_api

from cvfm import constants as const
from cvfm.exceptions import VNCVMICreationError

logger = logging.getLogger(__name__)


def generate_uuid(key):
    return str(uid.uuid3(uid.NAMESPACE_DNS, key))


class Model(object):
    def __init__(self, uuid):
        self.uuid = uuid

    def __eq__(self, other):
        return self.uuid == other.uuid

    def __ne__(self, other):
        return self.uuid != other.uuid

    def __hash__(self):
        return hash(self.uuid)


class VirtualMachineModel(Model):
    def __init__(self, name, vcenter_uuid, host_name, dpg_models):
        super(VirtualMachineModel, self).__init__(vcenter_uuid)
        self.name = name
        self.vcenter_uuid = vcenter_uuid
        self.host_name = host_name
        self.dpg_models = dpg_models
        self.property_filter = None

    def set_property_filter(self, property_filter):
        self.property_filter = property_filter

    def destroy_property_filter(self):
        self.property_filter.DestroyPropertyFilter()

    def detach_dpg(self, dpg_name):
        dpgs = [dpg for dpg in self.dpg_models if dpg.name == dpg_name]
        if len(dpgs) == 1:
            self.dpg_models.remove(dpgs[0])

    def has_interface_in_dpg(self, dpg_model):
        return dpg_model in self.dpg_models

    def attach_dpg(self, dpg_model):
        self.dpg_models.add(dpg_model)

    @classmethod
    def from_vmware_vm(cls, vmware_vm, dpg_models):
        return cls(
            name=vmware_vm.name,
            vcenter_uuid=vmware_vm.config.instanceUuid,
            host_name=vmware_vm.runtime.host.name,
            dpg_models=dpg_models,
        )

    def __repr__(self):
        return (
            "VirtualMachineModel(name={name}, vcenter_uuid={vcenter_uuid}, host_name={host_name}, "
            "dpg_models={dpg_models})".format(
                name=self.name,
                vcenter_uuid=self.vcenter_uuid,
                host_name=self.host_name,
                dpg_models=self.dpg_models,
            )
        )


class DistributedPortGroupModel(Model):
    def __init__(self, uuid, key, name, vlan_id, dvs_name):
        super(DistributedPortGroupModel, self).__init__(uuid)
        self.key = key
        self.name = name
        self.vlan_id = vlan_id
        self.dvs_name = dvs_name

    def to_vnc_vn(self, project):
        vnc_name = self.get_vnc_name(self.dvs_name, self.name)
        vnc_vn = vnc_api.VirtualNetwork(name=vnc_name, parent_obj=project)
        vnc_vn.set_uuid(self.uuid)
        vnc_vn.set_id_perms(const.ID_PERMS)
        return vnc_vn

    @classmethod
    def from_vmware_dpg(cls, vmware_dpg):
        vlan_id = vmware_dpg.config.defaultPortConfig.vlan.vlanId
        uuid = generate_uuid(vmware_dpg.key)
        key = vmware_dpg.key
        name = vmware_dpg.name
        dvs_name = vmware_dpg.config.distributedVirtualSwitch.name
        return cls(uuid, key, name, vlan_id, dvs_name)

    @staticmethod
    def get_vnc_name(dvs_name, dpg_name):
        return "{dvs_name}_{dpg_name}".format(
            dvs_name=dvs_name, dpg_name=dpg_name
        )

    def __repr__(self):
        return (
            "DistributePortGroupModel(uuid={uuid}, "
            "key={key}, name={name}, vlan_id={vlan_id}, "
            "dvs_name={dvs_name})".format(
                uuid=self.uuid,
                key=self.key,
                name=self.name,
                vlan_id=self.vlan_id,
                dvs_name=self.dvs_name,
            )
        )


class VirtualPortGroupModel(Model):
    def __init__(self, uuid, host_name, dvs_name):
        super(VirtualPortGroupModel, self).__init__(uuid)
        self.host_name = host_name
        self.dvs_name = dvs_name
        self.name = "{host_name}_{dvs_name}".format(
            host_name=self.host_name, dvs_name=self.dvs_name
        )

    def to_vnc_vpg(self, fabric):
        vnc_vpg = vnc_api.VirtualPortGroup(name=self.name, parent_obj=fabric)
        vnc_vpg.set_uuid(self.uuid)
        vnc_vpg.set_id_perms(const.ID_PERMS)
        return vnc_vpg

    @classmethod
    def from_vm_model(cls, vm_model):
        host_name = vm_model.host_name
        models = []
        for dpg_model in vm_model.dpg_models:
            dvs_name = dpg_model.dvs_name
            uuid = generate_uuid(
                "{host_name}_{dvs_name}".format(
                    host_name=host_name, dvs_name=dvs_name
                )
            )
            models.append(cls(uuid, host_name, dvs_name))
        return models

    def __repr__(self):
        return (
            "VirtualPortGroupModel(uuid={uuid}, name={name}, host_name={host_name}, "
            "dvs_name={dvs_name})".format(
                uuid=self.uuid,
                name=self.name,
                host_name=self.host_name,
                dvs_name=self.dvs_name,
            )
        )


class VirtualMachineInterfaceModel(Model):
    def __init__(self, uuid, host_name, dpg_model):
        super(VirtualMachineInterfaceModel, self).__init__(uuid)
        self.host_name = host_name
        self.dpg_model = dpg_model
        self.name = "{host_name}_{dvs_name}_{dpg_name}".format(
            host_name=self.host_name,
            dvs_name=self.dpg_model.dvs_name,
            dpg_name=self.dpg_model.name,
        )

    def to_vnc_vmi(self, project, fabric_vn):
        if fabric_vn is None:
            raise VNCVMICreationError(
                "Cannot create VNC VMI without a fabric VN."
            )

        vnc_vmi = vnc_api.VirtualMachineInterface(
            name=self.name, parent_obj=project
        )
        vnc_vmi.set_uuid(self.uuid)
        vnc_vmi.add_virtual_network(fabric_vn)
        vmi_properties = vnc_api.VirtualMachineInterfacePropertiesType(
            sub_interface_vlan_tag=self.dpg_model.vlan_id
        )
        vnc_vmi.set_virtual_machine_interface_properties(vmi_properties)
        vnc_vmi.set_id_perms(const.ID_PERMS)
        return vnc_vmi

    @classmethod
    def from_vm_model(cls, vm_model):
        models = []
        for dpg_model in vm_model.dpg_models:
            uuid = generate_uuid(
                "{host_name}_{dvs_name}_{dpg_name}".format(
                    host_name=vm_model.host_name,
                    dvs_name=dpg_model.dvs_name,
                    dpg_name=dpg_model.name,
                )
            )
            models.append(cls(uuid, vm_model.host_name, dpg_model))
        return models

    @property
    def vpg_uuid(self):
        return generate_uuid(
            "{host_name}_{dvs_name}".format(
                host_name=self.host_name, dvs_name=self.dpg_model.dvs_name
            )
        )

    def __repr__(self):
        return (
            "VirtualMachineInterfaceModel(uuid={uuid}, name={name}, host_name={host_name}, "
            "dpg_model={dpg_model})".format(
                uuid=self.uuid,
                name=self.name,
                host_name=self.host_name,
                dpg_model=self.dpg_model,
            )
        )


class PhysicalInterfaceModel(Model):
    def __init__(self, uuid, fabric_uuid, host_name, dvs_name):
        super(PhysicalInterfaceModel, self).__init__(uuid)
        self.fabric_uuid = fabric_uuid
        self.host_name = host_name
        self.dvs_name = dvs_name

    def __repr__(self):
        return (
            "PhysicalInterfaceModel(uuid={uuid}, fabric_uuid={fabric_uuid}, host_name={host_name}, "
            "dvs_name={dvs_name})".format(
                uuid=self.uuid,
                fabric_uuid=self.fabric_uuid,
                host_name=self.host_name,
                dvs_name=self.dvs_name,
            )
        )
