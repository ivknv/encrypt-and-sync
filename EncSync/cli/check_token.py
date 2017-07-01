#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import make_encsync, show_error
from ..EncSync import EncSync, AUTH_URL
from ..YandexDiskApi.Exceptions import YandexDiskError

def check_token(env):
    encsync, ret = make_encsync(env)

    if encsync is None:
        return ret

    try:
        if encsync.check_token():
            return 0
    except YandexDiskError as e:
        show_error("Yandex.Disk error: %s: %s" % (e.error_type, str(e)))
        return 1

    try:
        while True:
            print("Go to the following URL: %s" % AUTH_URL)
            code = input("Confirmation code: ")

            try:
                response = encsync.ynd.get_token(code)
            except YandexDiskError as e:
                show_error("Yandex.Disk error: %s: %s" % (e.error_type, str(e)))
                show_error("Failed to get token. Try again")
                continue

            token = response["data"]["access_token"]
            break

        encsync.set_token(token)
        enc_data = encsync.make_encrypted_data()
        EncSync.store_encrypted_data(enc_data, env["enc_data_path"], encsync.master_key)

        return 0
    except (KeyboardInterrupt, EOFError):
        return 130
