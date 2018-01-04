#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..Task import Task

__all__ = ["SyncTarget"]

class SyncTarget(Task):
    def __init__(self):
        Task.__init__(self)

        self._stage = None
        self.src = None
        self.dst = None
        
        self.skip_integrity_check = False
        self.total_children = 0
        self.name = None
        self.enable_scan = True

        self.add_event("stage_changed")
        self.add_event("integrity_check")
        self.add_event("integrity_check_finished")
        self.add_event("integrity_check_failed")
        self.add_event("diffs_started")
        self.add_event("diffs_failed")
        self.add_event("diffs_finished")

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
