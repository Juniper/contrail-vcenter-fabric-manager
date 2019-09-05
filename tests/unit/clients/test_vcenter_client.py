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
    with mock.patch("cvfm.clients.vcenter.SmartConnectNoSSL") as si:
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


@mock.patch("cvfm.clients.vcenter.time.sleep")
def test_is_vm_removed(_, vcenter_api_client, vmware_vm):
    # VM vm-1 still exists on esxi-1
    with mock.patch.object(vcenter_api_client, "_si") as si:
        si.content.searchIndex.FindByUuid.return_value = vmware_vm
        assert not vcenter_api_client.is_vm_removed(
            vmware_vm.config.instanceUuid, "esxi-1"
        )

    # VM vm-1 was removed from host esxi-1 and whole vCenter
    with mock.patch.object(vcenter_api_client, "_si") as si:
        si.content.searchIndex.FindByUuid.return_value = None
        assert vcenter_api_client.is_vm_removed(
            vmware_vm.config.instanceUuid, "esxi-1"
        )


@mock.patch("cvfm.clients.vcenter.time.sleep")
def test_is_vm_removed_host_is_none(_, vcenter_api_client, vmware_vm):
    vmware_vm.runtime.host = None

    with mock.patch.object(vcenter_api_client, "_si") as si:
        si.content.searchIndex.FindByUuid.return_value = vmware_vm
        assert not vcenter_api_client.is_vm_removed(
            vmware_vm.config.instanceUuid, "esxi-1"
        )


@mock.patch("cvfm.clients.vcenter.time.sleep")
def test_is_vm_removed_host_changed(_, vcenter_api_client, vmware_vm):
    with mock.patch.object(vcenter_api_client, "_si") as si:
        si.content.searchIndex.FindByUuid.return_value = vmware_vm
        assert not vcenter_api_client.is_vm_removed(
            vmware_vm.config.instanceUuid, "esxi-2"
        )


def test_vcenter_connection_lost(service_instance, vcenter_api_client):
    service_instance.content.propertyCollector.WaitForUpdatesEx.side_effect = (
        socket.error
    )

    with pytest.raises(exceptions.VCenterConnectionLostError):
        vcenter_api_client.wait_for_updates()


def test_wait_for_updates(service_instance, vcenter_api_client):
    update_set = mock.Mock()
    property_collector = service_instance.content.propertyCollector
    property_collector.WaitForUpdatesEx.return_value = update_set

    result = vcenter_api_client.wait_for_updates()

    assert result == update_set


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


def test_add_filter(service_instance, vcenter_api_client):
    obj = vim.ManagedObject(moId="moid")
    filters = ["latest-page"]

    vcenter_api_client.add_filter(obj, filters)

    property_collector = service_instance.content.propertyCollector
    property_collector.CreateFilter.assert_called_once()
    filter_spec = property_collector.CreateFilter.call_args[0][0]

    assert filter_spec.objectSet[0].obj == obj
    assert filter_spec.propSet[0].pathSet == ["latest-page"]
    assert filter_spec is not None


def test_get_host(vcenter_api_client):
    host = mock.Mock()
    host.configure_mock(name="esxi-1")

    with mock.patch.object(vcenter_api_client, "_host_view") as host_view:
        host_view.view = [host]
        assert vcenter_api_client.get_host("esxi-1") == host
        assert vcenter_api_client.get_host("esxi-2") is None
