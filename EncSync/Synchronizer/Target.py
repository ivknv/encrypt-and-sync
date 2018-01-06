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
        if self._stage == value:
            return

        self._stage = value
        self.emit_event("stage_changed")

    def get_n_done(self):
        return self.progress["finished"] + self.progress["failed"]
