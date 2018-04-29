#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import authenticate

def password_prompt(env):
    password, ret = authenticate(env, env["enc_data_path"])

    if password is None:
        return ret

    print(password)

    return 0
