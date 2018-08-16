# -*- coding: utf-8 -*-

from ..authenticator import Authenticator
from ..authenticator.exceptions import AuthenticatorError

from .common import show_error, make_config, recognize_path

__all__ = ["logout"]

def logout(env, paths):
    config, ret = make_config(env)

    if ret:
        return ret

    if not paths:
        paths = ["%s:///" % (k,) for k in Storage.registered_storages.keys()]

    for path in paths:
        path, path_type = recognize_path(path)

        try:
            authenticator = Authenticator.get_authenticator(path_type)()
        except UnknownAuthenticatorError:
            continue

        try:
            authenticator.logout(config, path, env)
        except AuthenticatorError as e:
            show_error("Failed to logout from %r: %s" % (path_type + "://" + path, e))
            ret = 1
        else:
            config.store_encrypted_data(env["enc_data_path"])

    return ret
