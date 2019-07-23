#!/usr/bin/env python
import logging
import os
import sys

import gevent
from cfgm_common import zkclient
from pysandesh import sandesh_logger as sand_logger

from cvfm.context import CVFMContext
from cvfm.exceptions import CVFMError
from cvfm.parser import CVFMArgumentParser

gevent.monkey.patch_all()

logger = logging.getLogger("cvfm")


def create_logger(cfg):
    introspect_config = cfg["introspect_config"]
    sandesh_logger = sand_logger.SandeshLogger("cvfm")
    sand_logger.SandeshLogger.set_logger_params(
        logger=sandesh_logger.logger(),
        enable_local_log=True,
        level=introspect_config["logging_level"],
        file=introspect_config["log_file"],
        enable_syslog=False,
        syslog_facility=None,
    )


def run_vcenter_fabric_manager(context):
    context.build()
    greenlets = [gevent.spawn(context.start)]
    gevent.joinall(greenlets, raise_error=True)


def zookeeper_connection_lost():
    logger.error("Connection to Zookeeper lost.")
    sys.exit(1)


def prepare_zookeeper_client(cfg):
    logger.info("Connecting to zookeeper...")
    zookeeper_client = zkclient.ZookeeperClient(
        "vcenter-fabric-manager",
        cfg["zookeeper_config"]["zookeeper_servers"],
        cfg["defaults_config"]["host_ip"],
    )
    zookeeper_client.set_lost_cb(zookeeper_connection_lost)
    return zookeeper_client


def main(cfg):
    create_logger(cfg)
    zookeeper_client = prepare_zookeeper_client(cfg)
    context = CVFMContext(cfg)

    logger.info("Waiting to be elected as master...")
    zookeeper_client.master_election(
        "/vcenter-fabric-manager",
        os.getpid(),
        run_vcenter_fabric_manager,
        context,
    )


if __name__ == "__main__":
    parser = CVFMArgumentParser()
    config = parser.parse_args(sys.argv[1:])
    try:
        main(config)
        sys.exit(0)
    except (CVFMError, zkclient.kazoo.exceptions.ConnectionClosedError) as exc:
        logger.exception(exc)
        logger.error("Restarting...")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        logger.critical("", exc_info=True)
        raise
