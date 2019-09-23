import mock
from pyVmomi import vim

from cvfm.clients import VCenterAPIClient
from tests import utils


class VCenterAPIMockClient(VCenterAPIClient):
    def __init__(self):
        self.portgroups = {}
        self.hosts = {}

    def create_dpg(self, vmware_dpg):
        event = mock.Mock(spec=vim.event.DVPortgroupCreatedEvent())
        event.net.network = vmware_dpg
        self.portgroups[vmware_dpg.key] = vmware_dpg
        return utils.wrap_into_update_set(event=event)

    def reconfigure_dpg(self, vmware_dpg, new_vlan_id):
        vmware_dpg.config.defaultPortConfig.vlan.vlanId = new_vlan_id
        event = mock.Mock(spec=vim.event.DVPortgroupReconfiguredEvent())
        event.net.network = vmware_dpg
        return utils.wrap_into_update_set(event=event)

    def rename_dpg(self, vmware_dpg, new_name):
        event = mock.Mock(spec=vim.event.DVPortgroupRenamedEvent())
        event.net.network = vmware_dpg
        event.oldName = vmware_dpg.name
        event.newName = new_name
        vmware_dpg.name = new_name
        return utils.wrap_into_update_set(event=event)

    def destroy_dpg(self, vmware_dpg):
        event = mock.Mock(spec=vim.event.DVPortgroupDestroyedEvent())
        event.net.name = vmware_dpg.name
        event.dvs.name = vmware_dpg.config.distributedVirtualSwitch.name
        del self.portgroups[vmware_dpg.key]
        return utils.wrap_into_update_set(event=event)

    def create_vm(self, vmware_vm):
        for network in vmware_vm.network:
            network.vm.append(vmware_vm)
            self.portgroups[network.key] = network

        host_name = vmware_vm.runtime.host.name
        host = self._get_or_create_host(host_name)
        host.vm.append(vmware_vm)
        self.hosts[host_name] = host

        event = mock.Mock(spec=vim.event.VmCreatedEvent())
        event.vm.vm = vmware_vm
        return utils.wrap_into_update_set(event=event)

    def remove_vm(
        self, vmware_vm, removed_from_vcenter=True, source_host_name=None
    ):
        if removed_from_vcenter:
            for network in vmware_vm.network:
                self.portgroups[network.key].vm.remove(vmware_vm)
            host_name = vmware_vm.runtime.host.name
            self.hosts[host_name].vm.remove(vmware_vm)
        else:
            host_name = source_host_name

        event = mock.Mock(spec=vim.event.VmRemovedEvent())
        event.vm.name = vmware_vm.name
        event.host.name = host_name
        event.host.host = self.hosts[host_name]
        return utils.wrap_into_update_set(event=event)

    def rename_vm(self, vmware_vm, new_name):
        event = mock.Mock(spec=vim.event.VmRenamedEvent())
        event.oldName = vmware_vm.name
        event.newName = new_name
        vmware_vm.name = new_name
        return utils.wrap_into_update_set(event=event)

    def get_vms_by_portgroup(self, portgroup_key):
        return self.portgroups[portgroup_key].vm

    def add_interface(self, vmware_vm, vmware_dpg):
        vmware_vm.network.append(vmware_dpg)
        self.portgroups[vmware_dpg.key].vm.append(vmware_vm)
        return utils.create_vm_reconfigured_update(vmware_vm, "add")

    def edit_interface(self, vmware_vm, old_vmware_dpg, new_vmware_dpg):
        self.remove_interface(vmware_vm, old_vmware_dpg)
        self.add_interface(vmware_vm, new_vmware_dpg)
        return utils.create_vm_reconfigured_update(vmware_vm, "edit")

    def remove_interface(self, vmware_vm, vmware_dpg):
        vmware_vm.network.remove(vmware_dpg)
        self.portgroups[vmware_dpg.key].vm.remove(vmware_vm)
        return utils.create_vm_reconfigured_update(vmware_vm, "remove")

    def is_vm_removed(self, vm_uuid, host_name):
        for host in list(self.hosts.values()):
            for vm in host.vm:
                if vm.config.instanceUuid == vm_uuid:
                    return False
        return True

    def change_host(self, vmware_vm, new_host_name):
        old_host_name = vmware_vm.runtime.host.name
        old_host = self.hosts[old_host_name]
        old_host.vm.remove(vmware_vm)
        new_host = self._get_or_create_host(new_host_name)
        new_host.vm.append(vmware_vm)
        vmware_vm.runtime.host.host = new_host
        vmware_vm.runtime.host.name = new_host_name
        return utils.create_host_change_update(vmware_vm, new_host)

    def get_all_portgroups(self):
        return list(self.portgroups.values())

    def get_all_vms(self):
        vms = []
        for host in list(self.hosts.values()):
            vms.extend(host.vm)
        return vms

    def _get_or_create_host(self, host_name):
        if not self.hosts.get(host_name):
            self.add_host(host_name)
        return self.hosts.get(host_name)

    def add_filter(self, obj, filters):
        return mock.Mock()

    def get_host(self, host_name):
        return self.hosts.get(host_name)

    def get_all_hosts(self):
        return list(self.hosts.values())

    def add_host(self, host_name):
        host = mock.Mock(vm=[])
        host.configure_mock(name=host_name)
        self.hosts[host_name] = host
