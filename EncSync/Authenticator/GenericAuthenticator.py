# -*- coding: utf-8 -*-

from .Authenticator import Authenticator

from ..Storage import Storage

__all__ = ["GenericAuthenticator"]

class GenericAuthenticator(Authenticator):
    """Only creates a storage object."""

    name = "_generic"

    def __init__(self, storage_name):
        self.storage_name = storage_name

    def login(self, config, *args, **kwargs):
        config.storages[self.storage_name] = Storage.get_storage(self.storage_name)(config)

    def logout(self, config, *args, **kwargs):
        pass
