#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..Task import Task

class SyncTask(Task):
    def __init__(self):
        Task.__init__(self)

        self.task_type = None # "new" or "rm"
        self.type = None # "f" or "d"
        self.path = None
        self._uploaded = 0
        self.size = 0

        self.add_event("uploaded_changed")
        self.add_event("filename_too_long")
        self.add_event("interrupted")

    @property
    def uploaded(self):
        return self._uploaded

    @uploaded.setter
    def uploaded(self, value):
        old_value = self._uploaded
        self._uploaded = value
        if value != old_value:
            self.emit_event("uploaded_changed")

class SyncTarget(Task):
    def __init__(self, synchronizer, local=None, remote=None):
        Task.__init__(self)
        self._stage = None
        self.local, self.remote = local, remote
        self.skip_integrity_check = False
        self.total_children = 0
        self.enable_scan = True

        self.add_event("stage_changed")
        self.add_event("local_scan")
        self.add_event("local_scan_failed")
        self.add_event("local_scan_finished")
        self.add_event("remote_scan")
        self.add_event("remote_scan_failed")
        self.add_event("remote_scan_finished")
        self.add_event("integrity_check")
        self.add_event("integrity_check_finished")
        self.add_event("integrity_check_failed")

    @property
    def stage(self):
        return self._stage

    @stage.setter
    def stage(self, value):
        self._stage = value
        self.emit_event("stage_changed")

    def get_n_done(self):
        return self.progress["finished"] + self.progress["failed"]

    def update_status(self):
        assert(self.parent is None)

        if self.status == "suspended":
            return

        syncing = self.progress["pending"]
        finished = self.progress["finished"]
        suspended = self.progress["suspended"]
        failed = self.progress["failed"]
        queued = self.total_children - (syncing + suspended + failed + finished)

        if finished == self.total_children:
            self.change_status("finished")
        elif syncing > 0 or queued > 0:
            self.change_status("pending")
        elif failed > 0:
            self.change_status("failed")
        elif suspended > 0:
            self.change_status("suspended")
