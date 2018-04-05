# -*- coding: utf-8 -*-

from ..Authenticator.YaDiskAuthenticator import YaDiskAuthenticator
from ..Authenticator.DropboxAuthenticator import DropboxAuthenticator
from ..Authenticator.GenericAuthenticator import GenericAuthenticator
from ..Authenticator.Exceptions import AuthenticatorError

from .common import show_error, make_config

__all__ = ["authenticate_storages"]

AUTHENTICATOR_TABLE = {"yadisk": YaDiskAuthenticator,
                       "dropbox": DropboxAuthenticator}

def authenticate_storages(env, storage_names=None):
    config, ret = make_config(env)

    if config is None:
        return ret

    if storage_names is None:
        storage_names = {i["type"] for i in config.folders.values()}

    for name in storage_names:
        authenticator = AUTHENTICATOR_TABLE.get(name)()

        if authenticator is None:
            authenticator = GenericAuthenticator(name)

        try:
            authenticator.login(config, env)
        except AuthenticatorError as e:
            show_error("Authentication error: %s" % (e,))
            return 1
        except (KeyboardInterrupt, EOFError):
            return 130

        config.store_encrypted_data(env["enc_data_path"])

    return 0
