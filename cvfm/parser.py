from future import standard_library

standard_library.install_aliases()
from builtins import object
from six.moves import configparser
import argparse
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
            "rabbit_config": {},
            "auth_config": {},
        }
        self._arg_parser = argparse.ArgumentParser()
        self._arg_parser.add_argument(
            "-c",
            action="store",
            dest="config_file",
            default="/etc/contrail/contrail-vcenter-fabric-manager/cvfm.conf",
        )
        self._parsed_config = configparser.ConfigParser()

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
        self._read_rabbit_config()
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
        introspect_config = self._read_config(
            "INTROSPECT", ints=["introspect_port"]
        )

        # This list cannot be parsed by generic _read_config, since its'
        # items are separated by spaces instead of commas
        collector_list = introspect_config.get("collectors")
        if collector_list:
            introspect_config["collectors"] = collector_list.split()
        if introspect_config.get("collectors"):
            random.shuffle(introspect_config["collectors"])

        log_level = introspect_config.get("logging_level")
        if log_level:
            introspect_config["logging_level"] = translate_logging_level(
                log_level
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
        vnc_config = self._read_config(
            section_name="VNC",
            ints=["api_server_port"],
            lists=["api_server_host"],
            booleans=["api_server_use_ssl", "api_server_insecure"],
        )
        if vnc_config.get("api_server_host"):
            random.shuffle(vnc_config["api_server_host"])
        self.config["vnc_config"] = vnc_config

    def _read_vcenter_config(self):
        vcenter_config = self._read_config(
            section_name="VCENTER",
            ints=["vc_port"],
            lists=["vc_preferred_api_versions"],
        )
        self.config["vcenter_config"] = vcenter_config

    def _read_zookeeper_config(self):
        zookeeper_config = self._read_config("ZOOKEEPER")
        self.config["zookeeper_config"] = zookeeper_config

    def _read_rabbit_config(self):
        rabbit_config = self._read_config(
            "RABBIT", ints=["rabbit_port", "rabbit_health_check_interval"]
        )
        rabbit_config["rabbit_ha_mode"] = False

        host_ip = self.config["defaults_config"]["host_ip"]
        rabbit_config["q_name"] = "cvfm.{}".format(socket.getfqdn(host_ip))
        rabbit_config["heartbeat_seconds"] = rabbit_config.get(
            "rabbit_health_check_interval"
        )

        self.config["rabbit_config"] = rabbit_config

    def _read_auth_config(self):
        auth_config = self._read_config("AUTH")
        self.config["auth_config"] = auth_config

    def _read_config(self, section_name, ints=(), lists=(), booleans=()):
        config_dict = {}
        if section_name in self._parsed_config.sections():
            config_dict.update(dict(self._parsed_config.items(section_name)))
            for int_param in ints:
                if int_param in self._parsed_config.options(section_name):
                    config_dict[int_param] = self._parsed_config.getint(
                        section_name, int_param
                    )
            for list_param in lists:
                if list_param in self._parsed_config.options(section_name):
                    config_dict[list_param] = self._parsed_config.get(
                        section_name, list_param
                    ).split(",")
            for bool_param in booleans:
                if bool_param in self._parsed_config.options(section_name):
                    config_dict[bool_param] = self._parsed_config.getboolean(
                        section_name, bool_param
                    )
        return config_dict
