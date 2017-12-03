#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from ..Task import Task
from .. import Paths

class ScanTarget(Task):
    def __init__(self, scan_type=None, name=None, path=None, filename_encoding=None):
        Task.__init__(self)

        assert(scan_type in (None, "local", "remote"))

        self.type = scan_type

        self.name = name
        self.path = path

        if path is not None:
            if scan_type == "local":
                self.path = os.path.abspath(os.path.expanduser(path))
            else:
                self.path = Paths.join_properly("/", path)

        self.filename_encoding = filename_encoding

        self.add_event("next_node")
        self.add_event("duplicates_found")
        self.add_event("scan_finished")
