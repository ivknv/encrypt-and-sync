# -*- coding: utf-8 -*-

import importlib

from .authenticator import Authenticator

__all__ = ["Authenticator"]

def _get_yadisk_authenticator():
    try:
        return importlib.import_module("eas.authenticator.yadisk_authenticator").YaDiskAuthenticator
    except ImportError as e:
        if e.name in ("yadisk", "requests"):
            raise ImportError("Missing optional dependency: %r" % (e.name,), name=e.name)

        raise e

def _get_dropbox_authenticator():
    try:
        return importlib.import_module("eas.authenticator.dropbox_authenticator").DropboxAuthenticator
    except ImportError as e:
        if e.name in ("dropbox", "requests"):
            raise ImportError("Missing optional dependency: %r" % (e.name,), name=e.name)

        raise e

def _get_sftp_authenticator():
    try:
        return importlib.import_module("eas.authenticator.sftp_authenticator").SFTPAuthenticator
    except ImportError as e:
        if e.name in ("pysftp", "paramiko"):
            raise ImportError("Missing optional dependency: %r" % (e.name,), name=e.name)

        raise e

Authenticator.register_lazy("yadisk", _get_yadisk_authenticator)
Authenticator.register_lazy("dropbox", _get_dropbox_authenticator)
Authenticator.register_lazy("sftp", _get_sftp_authenticator)
