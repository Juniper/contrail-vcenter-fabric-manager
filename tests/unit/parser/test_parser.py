import os
import mock
import pytest
import random
from cvfm import parser


@pytest.fixture
def argument_parser():
    return parser.CVFMArgumentParser()


@pytest.fixture
def arg_str():
    current_path = os.path.realpath(__file__)
    current_dir = os.path.dirname(current_path)
    config_path = os.path.join(current_dir, "test.conf")
    return "-c {}".format(config_path).split()


def test_sandesh_config_from_file(argument_parser, arg_str):
    sandesh_config = argument_parser.parse_args(arg_str)["sandesh_config"]

    assert sandesh_config.http_server_ip == "0.0.0.0"
    assert sandesh_config.sandesh_ssl_enable is True
    assert sandesh_config.introspect_ssl_enable is True
    assert sandesh_config.keyfile == "/path-to-sandesh-keyfile"
    assert sandesh_config.certfile == "/path-to-sandesh-certfile"
    assert sandesh_config.ca_cert == "/path-to-sandesh-cafile"


def test_introspect_config_from_file(argument_parser, arg_str):
    parsed_args = argument_parser.parse_args(arg_str)
    introspect_config = parsed_args["introspect_config"]

    assert sorted(introspect_config["collectors"]) == sorted(
        ["192.168.0.11:8086", "192.168.0.1:8086"]
    )
    assert introspect_config["logging_level"] == "SYS_INFO"
    assert introspect_config["log_file"] == "cvfm.log"
    assert introspect_config["introspect_port"] == 9099


def test_vnc_config_from_file(argument_parser, arg_str):
    vnc_config = argument_parser.parse_args(arg_str)["vnc_config"]

    assert sorted(vnc_config["api_server_host"]) == sorted(
        ["192.168.0.11", "192.168.0.1"]
    )
    assert vnc_config["api_server_port"] == 8082
    assert vnc_config["api_server_use_ssl"] is True
    assert vnc_config["api_server_insecure"] is True
    assert vnc_config["api_keyfile"] == "/path-to-api-keyfile"
    assert vnc_config["api_certfile"] == "/path-to-api-certfile"
    assert vnc_config["api_cafile"] == "/path-to-api-cafile"


def test_vcenter_config_from_file(argument_parser, arg_str):
    vcenter_config = argument_parser.parse_args(arg_str)["vcenter_config"]

    assert vcenter_config == {
        "vc_host": "192.168.0.2",
        "vc_port": 443,
        "vc_username": "admin",
        "vc_password": "password",
        "vc_preferred_api_versions": [
            "vim.version.version10",
            "vim.version.version11",
        ],
        "vc_datacenter": "dc",
    }


def test_zookeeper_config_from_file(argument_parser, arg_str):
    zookeeper_config = argument_parser.parse_args(arg_str)["zookeeper_config"]

    assert zookeeper_config == {
        "zookeeper_servers": "192.168.0.1:2181,192.168.0.11:2181"
    }


def test_rabbit_config_from_file(argument_parser, arg_str):
    with mock.patch("cvfm.parser.socket.getfqdn") as getfqdn:
        getfqdn.return_value = "hostname"
        rabbit_config = argument_parser.parse_args(arg_str)["rabbit_config"]

    assert rabbit_config["rabbit_hosts"] == "192.168.0.1,192.168.0.11"
    assert rabbit_config["rabbit_port"] == 5673
    assert rabbit_config["rabbit_user"] == "guest"
    assert rabbit_config["rabbit_password"] == "guest"
    assert rabbit_config["rabbit_vhost"] == "/"
    assert rabbit_config["rabbit_ha_mode"] is False
    assert rabbit_config["q_name"] == "cvfm.hostname"
    assert rabbit_config["heartbeat_seconds"] == 10
    assert rabbit_config["kombu_ssl_version"] == "sslv23"
    assert rabbit_config["kombu_ssl_certfile"] == "/path-to-rabbit-certfile"
    assert rabbit_config["kombu_ssl_keyfile"] == "/path-to-rabbit-keyfile"
    assert rabbit_config["kombu_ssl_ca_certs"] == "/path-to-rabbit-cafile"


def test_auth_config_from_file(argument_parser, arg_str):
    auth_config = argument_parser.parse_args(arg_str)["auth_config"]

    assert auth_config == {
        "auth_user": "admin",
        "auth_password": "admin",
        "auth_tenant": "admin",
        "auth_token_url": "auth-token-url",
    }
