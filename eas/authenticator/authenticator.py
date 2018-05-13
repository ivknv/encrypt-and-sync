# -*- coding: utf-8 -*-

import re

from .exceptions import UnknownAuthenticatorError

from ..common import LazyDict

__all__ = ["Authenticator"]

_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9-_.]{0,63}$")

class Authenticator(object):
    """
        This class is used for storage authentication.
        
        :cvar registered_authenticators: `LazyDict`, contains registered authenticator classes (don't touch it!)

        :cvar name: `str`, authenticator name, must match ^[a-zA-Z0-9_][a-zA-Z0-9-_.]{0,63}$
    """

    registered_authenticators = LazyDict()

    name = None

    @classmethod
    def validate(cls):
        """
            Validate the authenticator class.

            :raises ValueError: invalid authenticator class
        """

        if not cls.name:
            raise ValueError("authenticator name must be non-empty")

        if not _NAME_REGEX.match(cls.name):
            raise ValueError("invalid authenticator name: %r" % (cls.name,))

    @staticmethod
    def register_lazy(name, function):
        """
            Register the descendant authenticator class lazily.

            :param function: callable, must return the authenticator class

            :raises ValueError: invalid authenticator class
        """

        if not _NAME_REGEX.match(name):
            raise ValueError("invalid authenticator name: %r" % (name,))

        def wrapper():
            cls = function()
            cls.validate()

            return cls

        Authenticator.registered_authenticators[name] = wrapper

    @classmethod
    def register(cls):
        """
            Register the descendant authenticator class.
            
            :raises ValueError: invalid authenticator class
        """

        cls.validate()

        Authenticator.registered_authenticators[cls.name] = lambda: cls

    @classmethod
    def unregister(cls):
        """
            Unregister the descendant authenticator class.
            
            :raises UnknownAuthenticatorError: attempting to unregister an unregistered authenticator
        """

        try:
            Authenticator.registered_authenticators.pop(cls.name)
        except KeyError:
            raise UnknownAuthenticatorError("unregistered authenticator: %r" % (cls.name,))

    @staticmethod
    def get_authenticator(name):
        """
            Get a (registered) authenticator class by name.

            :param name: `str`, authenticator name

            :raises UnknownAuthenticatorError: requested authenticator is not registered

            :returns: corresponding `Authenticator`-based class
        """

        try:
            return Authenticator.registered_authenticators[name]
        except KeyError:
            raise UnknownAuthenticatorError("unregistered authenticator %r" % (name,))

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
