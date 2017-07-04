#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import common
from ..FileList import DuplicateList

def show_duplicates(env, paths):
    duplist = DuplicateList(env["config_dir"])
    duplist.create()
    
    for path in paths:
        path = common.recognize_path(path)[0]
        for duplicate in duplist.find_children(path):
            print("{} {}".format(duplicate[0], duplicate[1]))

    return 0
