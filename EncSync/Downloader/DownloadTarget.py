#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
from ..Task import Task

__all__ = ["DownloadTarget"]

class DownloadTarget(Task):
    def __init__(self):
        Task.__init__(self)

        self.type = None
        self.name = ""
        self.src = None
        self.dst = None
        self.src_path = ""
        self.dst_path = ""
        self.size = 0
        self.downloaded = 0
        self.children = []
        self.pool = []
        self.pool_lock = threading.Lock()
