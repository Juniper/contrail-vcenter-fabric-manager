import logging

from cvfm import models
from cvfm.exceptions import VNCPortValidationError
from cvfm.services.base import Service

__all__ = ["PhysicalInterfaceService", "validate_vnc_port"]

logger = logging.getLogger(__name__)


def validate_vnc_port(vnc_port):
    esxi_port_info = vnc_port.get_esxi_port_info()
    if not esxi_port_info:
        raise VNCPortValidationError(
            "No ESXi info could be read from port %s", vnc_port.name
        )
    dvs_name = esxi_port_info.get_dvs_name()
    if not dvs_name:
        raise VNCPortValidationError(
            "No DVS name could be read from port %s", vnc_port.name
        )
    pi_back_refs = vnc_port.get_physical_interface_back_refs()
    if not pi_back_refs:
        raise VNCPortValidationError(
            "No Physical Interfaces could be found for port %s", vnc_port.name
        )


class PhysicalInterfaceService(Service):
    def __init__(self, vcenter_api_client, vnc_api_client, database):
        super(PhysicalInterfaceService, self).__init__(
            vcenter_api_client, vnc_api_client, database
        )
        self._pr_to_fabric = None

    def get_pi_models_for_vpg(self, vpg_model):
        return self._database.get_pi_models_for_vpg(vpg_model)

    def _populate_pr_to_fabric(self):
        result = {}
        pr_list = self._vnc_api_client.read_all_physical_routers()
        for pr in pr_list:
            fabric_refs = pr.get_fabric_refs()
            if fabric_refs is None:
                continue
            fabric_uuid = fabric_refs[0]["uuid"]
            result[pr.uuid] = fabric_uuid
        return result

    def populate_db_with_pi_models(self):
        self._pr_to_fabric = self._populate_pr_to_fabric()
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
            except VNCPortValidationError:
                continue

    def _create_pis_for_port(self, vnc_node, vnc_port):
        validate_vnc_port(vnc_port)
        host_name = vnc_node.name
        dvs_name = vnc_port.get_esxi_port_info().get_dvs_name()
        vnc_pis = self._vnc_api_client.get_pis_by_port(vnc_port)
        self._create_pi_models_in_db(vnc_pis, host_name, dvs_name)

    def _create_pi_models_in_db(self, vnc_pis, host_name, dvs_name):
        pi_models = []
        for vnc_pi in vnc_pis:
            fabric_uuid = self._pr_to_fabric[vnc_pi.parent_uuid]
            pi_model = models.PhysicalInterfaceModel(
                vnc_pi.uuid, fabric_uuid, host_name, dvs_name
            )
            pi_models.append(pi_model)
        for pi_model in pi_models:
            self._database.add_pi_model(pi_model)
            logger.debug("%s saved into database", pi_model)
