#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..config import Config
from ..config.exceptions import InvalidEncryptedDataError
from .common import authenticate, show_error

__all__ = ["get_key"]

def get_key(env):
    master_password, ret = authenticate(env, env["enc_data_path"])

    if master_password is None:
        return ret

    config = Config()
    config.master_password = master_password

    try:
        config.load_encrypted_data(env["enc_data_path"])
        print(config.plain_key)
    except InvalidEncryptedDataError:
        show_error("Error: invalid encrypted data")
        return 1
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % (env["enc_data_path"],))
        return 1
    except IsADirectoryError:
        show_error("Error: %r is a directory" % (env["enc_data_path"],))
        return 1

    return 0
