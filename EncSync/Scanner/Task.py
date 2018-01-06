#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..Task import Task

__all__ = ["ScanTask"]

class ScanTask(Task):
    def __init__(self, scannable):
        Task.__init__(self)

        self.scannable = scannable

        self.add_event("interrupt")
        self.add_event("duplicates_found")
