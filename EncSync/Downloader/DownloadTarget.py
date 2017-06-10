#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
from ..Task import Task

class DownloadTarget(Task):
    def __init__(self):
        Task.__init__(self)

        self.type = None
        self.prefix = "/" # Remote prefix
        self.remote = "" # Must be unencrypted
        self.local = ""
        self.size = 0
        self.downloaded = 0
        self.children = []
        self.pool = []
        self.total_children = 0
        self.pool_lock = threading.Lock()

    def update_status(self):
        assert(self.parent is None)

        if self.status == "suspended":
            return

        downloading = self.progress["pending"]
        suspended = self.progress["suspended"]
        failed = self.progress["failed"]

        if downloading == 0 and suspended == 0 and failed == 0:
            self.change_status("finished")
        elif downloading > 0:
            self.change_status("pending")
        elif failed > 0:
            self.change_status("failed")
        elif suspended > 0:
            self.change_status("suspended")
