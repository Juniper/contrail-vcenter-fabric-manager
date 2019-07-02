import argparse
import ConfigParser
import random
import socket

import sandesh_common.vns.constants as sandesh_constants
from pysandesh.sandesh_base import SandeshConfig
from sandesh_common.vns.ttypes import Module


def translate_logging_level(level):
    # Default logging level during contrail deployment is SYS_NOTICE,
    # but python logging library hasn't notice level, so we have to translate
    # SYS_NOTICE to logging.INFO, because next available level is logging.WARN,
    # what is too high for normal vcenter-fabric-manager logging.
    if level == "SYS_NOTICE":
        return "SYS_INFO"
    return level


class CVFMArgumentParser(object):
    def __init__(self):
        self.config = {
            "defaults_config": {},
            "sandesh_config": None,
            "introspect_config": {},
            "vnc_config": {},
            "vcenter_config": {},
            "zookeeper_config": {},
            "auth_config": {},
        }
        self._arg_parser = argparse.ArgumentParser()
        self._arg_parser.add_argument(
            "-c",
            action="store",
            dest="config_file",
            default="/etc/contrail/contrail-vcenter-fabric-manager/cvfm.conf",
        )
        self._parsed_config = ConfigParser.SafeConfigParser()

    def parse_args(self, args_str=""):
        parsed_args, _ = self._arg_parser.parse_known_args(args=args_str)
        conf_file = parsed_args.config_file
        self._parsed_config.read(conf_file)
        self._read_defaults_config()
        self._read_sandesh_config()
        self._read_introspect_config()
        self._read_vnc_config()
        self._read_vcenter_config()
        self._read_zookeeper_config()
        self._read_auth_config()
        return self.config

    def _read_defaults_config(self):
        defaults_config = {}
        if "DEFAULTS" in self._parsed_config.sections():
            defaults_config.update(dict(self._parsed_config.items("DEFAULTS")))
        self.config["defaults_config"] = defaults_config

    def _read_sandesh_config(self):
        SandeshConfig.add_parser_arguments(self._arg_parser)
        sandesh_opts = SandeshConfig.get_default_options(
            ["SANDESH", "DEFAULTS"]
        )
        self._arg_parser.set_defaults(**sandesh_opts)
        SandeshConfig.update_options(sandesh_opts, self._parsed_config)
        self._arg_parser.set_defaults(**sandesh_opts)
        args, _ = self._arg_parser.parse_known_args()
        sandesh_config = SandeshConfig.from_parser_arguments(args)
        self.config["sandesh_config"] = sandesh_config

    def _read_introspect_config(self):
        introspect_config = {}
        if "INTROSPECT" in self._parsed_config.sections():
            introspect_config.update(
                dict(self._parsed_config.items("INTROSPECT"))
            )
            if "introspect_port" in self._parsed_config.options("INTROSPECT"):
                introspect_config[
                    "introspect_port"
                ] = self._parsed_config.getint("INTROSPECT", "introspect_port")
            if "collectors" in self._parsed_config.options("INTROSPECT"):
                introspect_config["collectors"] = self._parsed_config.get(
                    "INTROSPECT", "collectors"
                ).split()
                random.shuffle(introspect_config["collectors"])
            if "logging_level" in self._parsed_config.options("INTROSPECT"):
                introspect_config["logging_level"] = translate_logging_level(
                    self._parsed_config.get("INTROSPECT", "logging_level")
                )

        introspect_config.update(
            {
                "id": Module.VCENTER_FABRIC_MANAGER,
                "hostname": socket.gethostname(),
                "table": "ObjectContrailvCenterFabricManagerNode",
                "instance_id": sandesh_constants.INSTANCE_ID_DEFAULT,
                "introspect_port": sandesh_constants.ServiceHttpPortMap[
                    "contrail-vcenter-fabric-manager"
                ],
            }
        )
        introspect_config["name"] = sandesh_constants.ModuleNames[
            introspect_config["id"]
        ]
        introspect_config["node_type"] = sandesh_constants.Module2NodeType[
            introspect_config["id"]
        ]
        introspect_config["node_type_name"] = sandesh_constants.NodeTypeNames[
            introspect_config["node_type"]
        ]

        self.config["introspect_config"] = introspect_config

    def _read_vnc_config(self):
        vnc_config = {}
        if "VNC" in self._parsed_config.sections():
            vnc_config.update(dict(self._parsed_config.items("VNC")))
            if "api_server_use_ssl" in self._parsed_config.options("VNC"):
                vnc_config[
                    "api_server_use_ssl"
                ] = self._parsed_config.getboolean("VNC", "api_server_use_ssl")
            if "api_server_insecure" in self._parsed_config.options("VNC"):
                vnc_config[
                    "api_server_insecure"
                ] = self._parsed_config.getboolean(
                    "VNC", "api_server_insecure"
                )
            if "api_server_port" in self._parsed_config.options("VNC"):
                vnc_config["api_server_port"] = self._parsed_config.getint(
                    "VNC", "api_server_port"
                )
            if "api_server_host" in self._parsed_config.options("VNC"):
                vnc_config["api_server_host"] = self._parsed_config.get(
                    "VNC", "api_server_host"
                ).split(",")
                random.shuffle(vnc_config["api_server_host"])

        self.config["vnc_config"] = vnc_config

    def _read_vcenter_config(self):
        vcenter_config = {}
        if "VCENTER" in self._parsed_config.sections():
            vcenter_config.update(dict(self._parsed_config.items("VCENTER")))
            if "vc_port" in self._parsed_config.options("VCENTER"):
                vcenter_config["vc_port"] = self._parsed_config.getint(
                    "VCENTER", "vc_port"
                )
            if "vc_preferred_api_versions" in self._parsed_config.options(
                "VCENTER"
            ):
                vcenter_config[
                    "vc_preferred_api_versions"
                ] = self._parsed_config.get(
                    "VCENTER", "vc_preferred_api_versions"
                ).split(
                    ","
                )

        self.config["vcenter_config"] = vcenter_config

    def _read_zookeeper_config(self):
        zookeeper_config = {}
        if "ZOOKEEPER" in self._parsed_config.sections():
            zookeeper_config.update(
                dict(self._parsed_config.items("ZOOKEEPER"))
            )

        self.config["zookeeper_config"] = zookeeper_config

    def _read_auth_config(self):
        auth_config = {}
        if "AUTH" in self._parsed_config.sections():
            auth_config.update(dict(self._parsed_config.items("AUTH")))

        self.config["auth_config"] = auth_config
