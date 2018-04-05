# -*- coding: utf-8 -*-

__all__ = ["Authenticator"]

class Authenticator(object):
    """This class is used for storage authentication."""

    def login(self, config, *args, **kwargs):
        """
            Log into a storage.
            Should also store an instance of `Storage` in `config.storages`.

            :param config: `Config`, current configuration
            :param args: additional positional arguments
            :param args: additional keyword arguments
        """

        raise NotImplementedError

    def logout(self, config, *args, **kwargs):
        """
            Log out of a storage.

            :param config: `Config`, current configuration
            :param args: additional positional arguments
            :param args: additional keyword arguments
        """

        raise NotImplementedError
