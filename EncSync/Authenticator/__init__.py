# -*- coding: utf-8 -*-

import importlib

from .Authenticator import Authenticator
from .GenericAuthenticator import GenericAuthenticator

__all__ = ["Authenticator"]

GenericAuthenticator.register()

Authenticator.register_lazy(
    "yadisk",
    lambda: importlib.import_module("EncSync.Authenticator.YaDiskAuthenticator").YaDiskAuthenticator)

Authenticator.register_lazy(
    "dropbox",
    lambda: importlib.import_module("EncSync.Authenticator.DropboxAuthenticator").DropboxAuthenticator)
