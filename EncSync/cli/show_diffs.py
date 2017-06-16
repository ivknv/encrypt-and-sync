#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from . import common
from ..FileComparator import compare_lists

def print_diff(diff):
    print("{} {} {}".format(diff[0], diff[1], diff[2].path))

def show_diffs(env, local, remote):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    local = os.path.expanduser(os.path.abspath(local))
    if not remote.startswith("/"):
        remote = "/" + remote

    for diff in compare_lists(encsync, local, remote, env["config_dir"]):
        print_diff(diff)

    return 0
