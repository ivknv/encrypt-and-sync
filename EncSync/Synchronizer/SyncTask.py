#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..Task import Task

class SyncTask(Task):
    def __init__(self):
        Task.__init__(self)
        self.diff = None
        self.path = None
        self.uploaded = 0
        self.size = 0

class SyncTarget(Task):
    def __init__(self, synchronizer, local=None, remote=None):
        Task.__init__(self)
        self.stage = None
        self.local, self.remote = local, remote
        self.skip_integrity_check = False
        self.total_children = 0
        self.enable_scan = True

        self.add_event("scan_finished")
        self.add_event("integrity_check_finished")
        self.add_event("integrity_check_failed")

    def get_n_done(self):
        return self.progress["finished"] + self.progress["failed"]

    def update_status(self):
        assert(self.parent is None)

        syncing = self.progress["pending"]
        suspended = self.progress["suspended"]
        failed = self.progress["failed"]

        if self.status == "suspended":
            return

        if syncing == 0 and suspended == 0 and failed == 0:
            self.change_status("finished")
        elif syncing > 0:
            self.change_status("pending")
        elif failed > 0:
            self.change_status("failed")
        elif suspended > 0:
            self.change_status("suspended")
