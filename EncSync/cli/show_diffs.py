#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from . import common
from ..FileComparator import compare_lists

global_vars = common.global_vars

def print_diff(diff):
    print("{} {} {}".format(diff[0], diff[1], diff[2].path))

def show_diffs(local, remote):
    encsync = common.make_encsync()

    if encsync is None:
        return 130

    local = os.path.expanduser(os.path.abspath(local))
    if not remote.startswith("/"):
        remote = "/" + remote

    for diff in compare_lists(encsync, local, remote):
        print_diff(diff)

    return 0
