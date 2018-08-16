# -*- coding: utf-8 -*-

from ..authenticator import Authenticator
from ..authenticator.exceptions import AuthenticatorError, UnknownAuthenticatorError

from .common import show_error, make_config, recognize_path

__all__ = ["authenticate_storages"]

def authenticate_storages(env, paths=None, auth_cache=None):
    config, ret = make_config(env)

    if auth_cache is None:
        # This is to avoid unnecessary authentication
        # Should contain anything that is hashable (e.g. host, port, username)
        auth_cache = set()

    if config is None:
        return ret

    if paths is None:
        paths = [i["type"] + "://" + i["path"] for i in config.folders.values()]

    for path in paths:
        path, path_type = recognize_path(path)

        try:
            if path_type == "_generic":
                authenticator = Authenticator.get_authenticator("_generic")(path_type)
            else:
                authenticator = Authenticator.get_authenticator(path_type)()
        except UnknownAuthenticatorError:
            authenticator = Authenticator.get_authenticator("_generic")(path_type)

        try:
            auth_id = authenticator.get_auth_id(config, path, env)

            if auth_id in auth_cache:
                continue

            authenticator.login(config, path, env)
        except AuthenticatorError as e:
            show_error("Authentication error: %s" % (e,))
            return 1
        except (KeyboardInterrupt, EOFError):
            return 130

        auth_cache.add(auth_id)

        config.store_encrypted_data(env["enc_data_path"])

    return 0
