# -*- coding: utf-8 -*-

import importlib

from .authenticator import Authenticator
from .generic_authenticator import GenericAuthenticator

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

GenericAuthenticator.register()

Authenticator.register_lazy("yadisk", _get_yadisk_authenticator)
Authenticator.register_lazy("dropbox", _get_dropbox_authenticator)
