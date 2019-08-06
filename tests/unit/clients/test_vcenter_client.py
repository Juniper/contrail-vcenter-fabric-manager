import socket

import gevent
import mock
import pytest
from pyVmomi import vim
from cvfm import clients, exceptions
from cvfm.exceptions import VCenterConnectionLostError


@pytest.fixture
def service_instance():
    return mock.Mock()


@pytest.fixture
def pg_view():
    return mock.Mock(view=[])


@pytest.fixture
def vcenter_api_client(service_instance, pg_view):
    with mock.patch("cvfm.clients.SmartConnectNoSSL") as si:
        si.return_value = service_instance
        service_instance.content.viewManager.CreateContainerView.return_value = (
            pg_view
        )
        return clients.VCenterAPIClient({})


def test_get_vms_for_portgroup(
    service_instance, vcenter_api_client, vmware_vm, vmware_dpg, pg_view
):
    vmware_dpg.vm = [vmware_vm]
    pg_view.view = [vmware_dpg]
    content = mock.Mock()
    content.searchIndex.FindByUuid.return_value = vmware_vm
    service_instance.content = content
    result = vcenter_api_client.get_vms_by_portgroup("dvportgroup-1")
    not_found = vcenter_api_client.get_vms_by_portgroup("dvportgroup-2")

    assert result == [vmware_vm]
    assert not_found == []


@mock.patch("cvfm.clients.time.sleep")
def test_is_vm_removed(_, vcenter_api_client, vmware_vm):
    # VM vm-1 still exists on esxi-1
    assert not vcenter_api_client.is_vm_removed(
        vmware_vm.config.instanceUuid, "esxi-1"
    )

    # VM vm-1 was removed from host esxi-1 and whole vCenter
    with mock.patch.object(vcenter_api_client, "_si") as si:
        si.content.searchIndex.FindByUuid.return_value = None
        assert vcenter_api_client.is_vm_removed(
            vmware_vm.config.instanceUuid, "esxi-1"
        )


def test_vcenter_connection_lost(service_instance, vcenter_api_client):
    service_instance.content.propertyCollector.WaitForUpdatesEx.side_effect = (
        socket.error
    )

    with pytest.raises(exceptions.VCenterConnectionLostError):
        vcenter_api_client.wait_for_updates()


def test_wait_for_updates_timeout(service_instance, vcenter_api_client):
    service_instance.content.propertyCollector.WaitForUpdatesEx.side_effect = (
        gevent.Timeout
    )

    with pytest.raises(VCenterConnectionLostError):
        vcenter_api_client.wait_for_updates()


def test_event_history_collector(service_instance, vcenter_api_client):
    ehc_mock = mock.Mock()
    event_manager = service_instance.content.eventManager
    event_manager.CreateCollectorForEvents.return_value = ehc_mock
    events = ["VmCreatedEvent"]

    with mock.patch.object(
        vcenter_api_client, "_datacenter", spec=vim.ManagedEntity
    ):
        ehc = vcenter_api_client.create_event_history_collector(events)

    assert ehc is ehc_mock
    filter_spec = event_manager.CreateCollectorForEvents.call_args[1]["filter"]
    assert filter_spec.type == [vim.event.VmCreatedEvent]
