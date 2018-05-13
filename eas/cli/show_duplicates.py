#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3

from . import common
from ..filelist import DuplicateList

__all__ = ["show_duplicates"]

def show_duplicates(env, paths):
    for path in paths:
        path, path_type = common.recognize_path(path)
        duplist = DuplicateList(path_type, env["db_dir"])

        try:
            for duplicate in duplist.find_children(path):
                print("%s %s" % (duplicate[0], duplicate[2]))
        except sqlite3.OperationalError:
            pass

    return 0
