#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..Task import Task

class ScanTarget(Task):
    def __init__(self, scan_type=None, path=None):
        Task.__init__(self)

        assert(scan_type in (None, "local", "remote"))

        self.type = scan_type

        self.path = path
