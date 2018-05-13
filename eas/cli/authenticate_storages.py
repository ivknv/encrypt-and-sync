# -*- coding: utf-8 -*-

from ..authenticator import Authenticator
from ..authenticator.exceptions import AuthenticatorError, UnknownAuthenticatorError

from .common import show_error, make_config

__all__ = ["authenticate_storages"]

def authenticate_storages(env, storage_names=None):
    config, ret = make_config(env)

    if config is None:
        return ret

    if storage_names is None:
        storage_names = {i["type"] for i in config.folders.values()}

    for name in storage_names:
        try:

            if name == "_generic":
                authenticator = Authenticator.get_authenticator("_generic")(name)
            else:
                authenticator = Authenticator.get_authenticator(name)()
        except UnknownAuthenticatorError:
            authenticator = Authenticator.get_authenticator("_generic")(name)

        try:
            authenticator.login(config, env)
        except AuthenticatorError as e:
            show_error("Authentication error: %s" % (e,))
            return 1
        except (KeyboardInterrupt, EOFError):
            return 130

        config.store_encrypted_data(env["enc_data_path"])

    return 0
