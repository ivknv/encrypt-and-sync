#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yadisk

from .common import make_encsync, show_error
from ..EncSync import EncSync

def check_token(env):
    encsync, ret = make_encsync(env)

    if encsync is None:
        return ret

    try:
        if encsync.ynd.check_token():
            return 0
    except yadisk.exceptions.YaDiskError as e:
        show_error("Yandex.Disk error: %s: %s" % (e.error_type, str(e)))
        return 1

    try:
        while True:
            print("Go to the following URL: %s" % encsync.ynd.get_code_url())
            code = input("Confirmation code: ")

            try:
                response = encsync.ynd.get_token(code)
            except yadisk.exceptions.YaDiskError as e:
                show_error("Yandex.Disk error: %s: %s" % (e.error_type, str(e)))
                show_error("Failed to get token. Try again")
                continue

            token = response.access_token
            break

        encsync.set_token(token)
        enc_data = encsync.make_encrypted_data()
        EncSync.store_encrypted_data(enc_data, env["enc_data_path"], encsync.master_key)

        return 0
    except (KeyboardInterrupt, EOFError):
        return 130
