# -*- coding: utf-8 -*-

from .authenticator import Authenticator

from ..storage import Storage
from ..storage.exceptions import UnknownStorageError
from ..cli.common import show_error

__all__ = ["GenericAuthenticator"]

class GenericAuthenticator(Authenticator):
    """Only creates a storage object."""

    name = "_generic"

    def __init__(self, storage_name):
        self.storage_name = storage_name

    def login(self, config, *args, **kwargs):
        try:
            config.storages[self.storage_name] = Storage.get_storage(self.storage_name)(config)
        except UnknownStorageError as e:
            show_error("Error: %s" % (e,))

    def logout(self, config, *args, **kwargs):
        pass
