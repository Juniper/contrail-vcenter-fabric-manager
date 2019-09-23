from builtins import next
from builtins import range
from builtins import object
import atexit
import logging
import time

import gevent

from cvfm import constants as const
from cvfm.clients.utils import api_client_error_translator, raises_socket_error
from cvfm.constants import WAIT_FOR_UPDATE_TIMEOUT
from cvfm.exceptions import VCenterConnectionLostError
from pyVim.connect import Disconnect, SmartConnectNoSSL
from pyVmomi import vim, vmodl

__all__ = ["VCenterAPIClient"]

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


@api_client_error_translator(raises_socket_error)
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
            return next((obj for obj in container.view if obj.name == name))
        except StopIteration:
            return None

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

    def make_wait_options(self, max_wait_seconds):
        self._wait_options.maxWaitSeconds = max_wait_seconds

    def wait_for_updates(self):
        timeout = gevent.Timeout(WAIT_FOR_UPDATE_TIMEOUT * 2)
        timeout.start()
        try:
            update_set = self._property_collector.WaitForUpdatesEx(
                self._version, self._wait_options
            )
            timeout.cancel()
            if update_set:
                self._version = update_set.version
        except gevent.Timeout:
            raise VCenterConnectionLostError("Wait for Updates timed out")
        finally:
            timeout.cancel()
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
            return next((dpg for dpg in all_dpgs if dpg.key == key))
        except StopIteration:
            return None

    def get_host(self, hostname):
        all_hosts = self.get_all_hosts()
        try:
            return next((host for host in all_hosts if host.name == hostname))
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
