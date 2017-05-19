#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import common
from ..FileList import DuplicateList

global_vars = common.global_vars

def show_duplicates(paths):
    #encsync = common.make_encsync()

    duplist = DuplicateList()
    
    for path in paths:
        path = common.recognize_path(path)[0]
        for duplicate in duplist.find_children(path):
            print("{} {}".format(duplicate[0], duplicate[1]))
