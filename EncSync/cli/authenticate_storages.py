# -*- coding: utf-8 -*-

from .authenticators import authenticate_yadisk

from ..EncSync import EncSync
from ..Storage import get_storage

from .common import make_encsync

__all__ = ["authenticate_storages"]

STORAGE_TABLE = {"yadisk": authenticate_yadisk}

def authenticate_generic_storage(env, name):
    encsync, ret = make_encsync(env)

    if encsync is None:
        return ret

    encsync.storages[name] = get_storage(name)(encsync)

def authenticate_storages(env):
    encsync, ret = make_encsync(env)

    if encsync is None:
        return ret

    storages = {j for i in encsync.targets.values()
                  for j in (i["src"]["name"], i["dst"]["name"])}

    for name in storages:
        authenticate_storage = STORAGE_TABLE.get(name)

        if authenticate_storage is None:
            authenticate_storage = lambda env: authenticate_generic_storage(env, name)

        ret = authenticate_storage(env)

        if ret:
            return ret

        enc_data = encsync.make_encrypted_data()
        EncSync.store_encrypted_data(enc_data, env["enc_data_path"], encsync.master_key)

    return 0
