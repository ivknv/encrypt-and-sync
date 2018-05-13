# -*- coding: utf-8 -*-

from ..authenticator import Authenticator
from ..authenticator.exceptions import AuthenticatorError

from .common import show_error, make_config

__all__ = ["logout"]

def logout(env, authenticator_names):
    config, ret = make_config(env)

    if ret:
        return ret

    if not authenticator_names:
        authenticator_names = Authenticator.registered_authenticators.keys()

    for authenticator_name in authenticator_names:
        authenticator = Authenticator.get_authenticator(authenticator_name)()

        try:
            authenticator.logout(config, env)
        except AuthenticatorError as e:
            show_error("Failed to logout from %r: %s" % (authenticator_name, e))
            ret = 1
        else:
            config.store_encrypted_data(env["enc_data_path"])

    return ret
