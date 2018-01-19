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
        token_valid = env.get("no_auth_check", False)

        if not token_valid:
            token_valid = y.check_token(n_retries=1)
            refresh_token = encsync.encrypted_data.get("yadisk_refresh_token", "")

            if not token_valid and refresh_token:
                try:
                    response = y.refresh_token(refresh_token)
                except yadisk.exceptions.UnauthorizedError as e:
                    pass
                else:
                    token = response.access_token
                    refresh_token = response.refresh_token

                    encsync.encrypted_data["yadisk_token"] = token
                    encsync.encrypted_data["yadisk_refresh_token"] = refresh_token

                    token_valid = True

        if token_valid:
            encsync.storages["yadisk"] = YaDiskStorage(encsync)
            return 0
    except YaDiskError as e:
        show_error("Yandex.Disk error: %s: %s" % (e.error_type, e))
        return 1

    try:
        token = None
        refresh_token = None

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
            refresh_token = response.refresh_token
            break

        encsync.encrypted_data["yadisk_token"] = token
        encsync.encrypted_data["yadisk_refresh_token"] = refresh_token

        encsync.storages["yadisk"] = YaDiskStorage(encsync)

        return 0
    except (KeyboardInterrupt, EOFError):
        return 130
