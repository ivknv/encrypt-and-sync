#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..Task import Task

__all__ = ["ScanTarget"]

class ScanTarget(Task):
    def __init__(self, scan_type, encrypted, storage, name, path, filename_encoding=None):
        Task.__init__(self)

        assert(scan_type in ("src", "dst"))

        self.type = scan_type
        self.encrypted = encrypted
        self.storage = storage

        self.name = name
        self.path = path
        self.filename_encoding = filename_encoding

        self.add_event("next_node")
        self.add_event("duplicates_found")
        self.add_event("scan_finished")
