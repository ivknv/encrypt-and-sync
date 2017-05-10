#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from . import common
from ..EncSync import AUTH_URL

global_vars = common.global_vars

def check_token():
    encsync = common.make_encsync()

    if encsync.check_token():
        return

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
    encsync.store_config(global_vars["config"])
