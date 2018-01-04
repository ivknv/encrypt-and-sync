# -*- coding: utf-8 -*-

import yadisk
from yadisk.exceptions import YaDiskError

from ..common import show_error, make_encsync
from ...Storage import YaDiskStorage
from ...constants import YADISK_APP_ID, YADISK_APP_SECRET

__all__ = ["authenticate_yadisk"]

def authenticate_yadisk(env):
    encsync, ret = make_encsync(env)

    if encsync is None:
        return ret

    y = yadisk.YaDisk(YADISK_APP_ID, YADISK_APP_SECRET,
                      encsync.encrypted_data.get("yadisk_token", ""))

    try:
        if env.get("no_auth_check", False) or y.check_token(n_retries=1):
            encsync.storages["yadisk"] = YaDiskStorage(encsync)
            return 0
    except YaDiskError as e:
        show_error("Yandex.Disk error: %s: %s" % (e.error_type, e))
        return 1

    try:
        while True:
            print("Go to the following URL: %s" % y.get_code_url())
            code = input("Confirmation code: ")

            try:
                response = y.get_token(code)
            except YaDiskError as e:
                show_error("Yandex.Disk error: %s: %s" % (e.error_type, e))
                show_error("Failed to get a token. Try again")
                continue

            token = response.access_token
            break

        encsync.encrypted_data["yadisk_token"] = token

        encsync.storages["yadisk"] = YaDiskStorage(encsync)

        return 0
    except (KeyboardInterrupt, EOFError):
        return 130
