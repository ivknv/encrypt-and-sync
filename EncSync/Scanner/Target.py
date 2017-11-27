#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..Task import Task

class ScanTarget(Task):
    def __init__(self, scan_type=None, name=None, path=None):
        Task.__init__(self)

        assert(scan_type in (None, "local", "remote"))

        self.type = scan_type

        self.name = name
        self.path = path

        self.add_event("next_node")
        self.add_event("duplicates_found")
        self.add_event("scan_finished")
