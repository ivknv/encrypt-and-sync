# -*- coding: utf-8 -*-

from .authenticators import authenticate_yadisk, authenticate_dropbox

from ..Storage import Storage

from .common import make_config

__all__ = ["authenticate_storages"]

STORAGE_TABLE = {"yadisk": authenticate_yadisk,
                 "dropbox": authenticate_dropbox}

def authenticate_generic_storage(env, name):
    config, ret = make_config(env)

    if config is None:
        return ret

    config.storages[name] = Storage.get_storage(name)(config)

def authenticate_storages(env, storage_names=None):
    config, ret = make_config(env)

    if config is None:
        return ret

    if storage_names is None:
        storage_names = {i["type"] for i in config.folders.values()}

    for name in storage_names:
        authenticate_storage = STORAGE_TABLE.get(name)

        if authenticate_storage is None:
            authenticate_storage = lambda env: authenticate_generic_storage(env, name)

        ret = authenticate_storage(env)

        if ret:
            return ret

        config.store_encrypted_data(env["enc_data_path"])

    return 0
