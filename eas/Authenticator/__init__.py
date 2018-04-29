# -*- coding: utf-8 -*-

import importlib

from .Authenticator import Authenticator
from .GenericAuthenticator import GenericAuthenticator

__all__ = ["Authenticator"]

def _get_yadisk_authenticator():
    try:
        return importlib.import_module("eas.Authenticator.YaDiskAuthenticator").YaDiskAuthenticator
    except ImportError as e:
        if e.name in ("yadisk", "requests"):
            raise ImportError("Missing optional dependency: %r" % (e.name,), name=e.name)

        raise e

def _get_dropbox_authenticator():
    try:
        return importlib.import_module("eas.Authenticator.DropboxAuthenticator").DropboxAuthenticator
    except ImportError as e:
        if e.name in ("dropbox", "requests"):
            raise ImportError("Missing optional dependency: %r" % (e.name,), name=e.name)

        raise e

GenericAuthenticator.register()

Authenticator.register_lazy("yadisk", _get_yadisk_authenticator)
Authenticator.register_lazy("dropbox", _get_dropbox_authenticator)
