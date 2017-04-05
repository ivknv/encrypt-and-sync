#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import Counter

from ..Task import Task

class DownloadTask(Task):
    def __init__(self):
        Task.__init__(self)

        self.type = None
        self.prefix = "/"
        self.remote = ""
        self.dec_remote = None
        self.IVs = None
        self.local = ""
        self.size = 0
        self.downloaded = 0
        self.link = None
        self.total_children = 0

    def copy(self):
        copy = DownloadTask()
        copy.status = self.status
        copy.parent = self.parent
        copy.total_children = self.total_children
        copy.progress = Counter(self.progress)
        copy.type = self.type
        copy.prefix = self.prefix
        copy.remote = self.remote
        copy.dec_remote = self.dec_remote
        copy.local = self.local
        copy.size = self.size
        copy.downloaded = self.downloaded
        copy.link = self.link

        return copy

    def obtain_link(self, ynd):
        if self.link is not None:
            return

        response = ynd.get_download_link(self.remote)
        if not response["success"]:
            self.change_status("failed")
            return

        self.link = response["data"]["href"]
