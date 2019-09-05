import functools
import logging
import socket

from vnc_api import vnc_api

from cvfm.exceptions import VCenterConnectionLostError, VNCConnectionLostError

logger = logging.getLogger(__name__)


def raises_vnc_conn_error(func):
    @functools.wraps(func)
    def wrapper_raises_conn_error(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except vnc_api.ConnectionError:
            raise VNCConnectionLostError("Connection to VNC lost.")

    return wrapper_raises_conn_error


def raises_socket_error(func):
    @functools.wraps(func)
    def wrapper_raises_socket_error(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except socket.error:
            raise VCenterConnectionLostError("Connection to vCenter lost.")

    return wrapper_raises_socket_error


def api_client_error_translator(decorator):
    def decorate(cls):
        for attr in vars(cls):
            if callable(getattr(cls, attr)):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls

    return decorate
