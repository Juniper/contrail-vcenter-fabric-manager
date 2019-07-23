#!/usr/bin/env python
import logging
import os
import sys

import gevent
from cfgm_common import zkclient

from cvfm.context import CVFMContext
from cvfm.exceptions import CVFMError
from cvfm.parser import CVFMArgumentParser

gevent.monkey.patch_all()

logger = logging.getLogger("cvfm")


def run_vcenter_fabric_manager(context):
    context.build()
    greenlets = [gevent.spawn(context.start)]
    gevent.joinall(greenlets, raise_error=True)


def main(cfg):
    context = CVFMContext(cfg)
    context.configure_logger()
    zookeeper_client = context.build_zookeeper_client()

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
