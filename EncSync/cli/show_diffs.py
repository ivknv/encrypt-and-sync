#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import common
from ..FileComparator import compare_lists

__all__ = ["show_diffs"]

def print_diff(diff):
    print("%s %s %s" % (diff["type"], diff["node_type"], diff["path"]))

def show_diffs(env, name):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    for diff in compare_lists(encsync, name, env["db_dir"]):
        print_diff(diff)

    return 0
