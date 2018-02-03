# -*- coding: utf-8 -*-

from .authenticators import authenticate_yadisk

from ..Storage import get_storage

from .common import make_config

__all__ = ["authenticate_storages"]

STORAGE_TABLE = {"yadisk": authenticate_yadisk}

def authenticate_generic_storage(env, name):
    config, ret = make_config(env)

    if config is None:
        return ret

    config.storages[name] = get_storage(name)(config)

def authenticate_storages(env):
    config, ret = make_config(env)

    if config is None:
        return ret

    storages = {j for i in config.targets.values()
                  for j in (i["src"]["name"], i["dst"]["name"])}

    for name in storages:
        authenticate_storage = STORAGE_TABLE.get(name)

        if authenticate_storage is None:
            authenticate_storage = lambda env: authenticate_generic_storage(env, name)

        ret = authenticate_storage(env)

        if ret:
            return ret

        config.store_encrypted_data(env["enc_data_path"])

    return 0
