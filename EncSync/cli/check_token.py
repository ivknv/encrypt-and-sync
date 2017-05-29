#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from . import common
from ..EncSync import EncSync, AUTH_URL

def check_token(env):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret
    
    if encsync.check_token():
        return 0

    try:
        while True:
            print("Go to the following URL: {}".format(AUTH_URL))
            code = input("Enter the confirmation code here: ")
            
            response = encsync.ynd.get_token(code)

            if response["success"]:
                token = response["data"]["access_token"]
                break
            else:
                print("Failed to get token. Try again", file=sys.stderr)

        encsync.set_token(token)
        config = encsync.make_config()
        EncSync.store_config(config, env["config_path"], encsync.master_key)

        return 0
    except (KeyboardInterrupt, EOFError):
        return 130
