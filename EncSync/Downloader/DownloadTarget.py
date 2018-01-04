#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
from ..Task import Task

class DownloadTarget(Task):
    def __init__(self, name):
        Task.__init__(self)

        self.type = None
        self.name = name
        self.src = None
        self.dst = None
        self.src_path = ""
        self.dst_path = ""
        self.size = 0
        self.downloaded = 0
        self.children = []
        self.pool = []
        self.total_children = 0
        self.pool_lock = threading.Lock()

        self.add_event("not_found_in_db")

    def update_status(self):
        assert(self.parent is None)

        if self.status == "suspended":
            return

        downloading = self.progress["pending"]
        finished = self.progress["finished"]
        suspended = self.progress["suspended"]
        failed = self.progress["failed"]
        queued = self.total_children - (downloading + finished + failed)

        if finished == self.total_children:
            self.change_status("finished")
        elif downloading > 0 or queued > 0:
            self.change_status("pending")
        elif failed > 0:
            self.change_status("failed")
        elif suspended > 0:
            self.change_status("suspended")
