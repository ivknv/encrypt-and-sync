#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import Counter

from ..Task import Task

class DownloadTask(Task):
    def __init__(self):
        Task.__init__(self)

        self.type = None
        self.prefix = "/"
        self.remote = "" # TODO make it an instance of EncPath
        self.dec_remote = None
        self.IVs = None
        self.local = ""
        self.size = 0
        self.modified = 0
        self._downloaded = 0
        self.link = None
        self.total_children = 0

        self.add_event("downloaded_changed")
        self.add_event("obtain_link_failed")

    @property
    def downloaded(self):
        return self._downloaded

    @downloaded.setter
    def downloaded(self, value):
        old_value = self._downloaded
        self._downloaded = value

        self.emit_event("downloaded_changed")

        if self.parent is not None:
            self.parent.downloaded += value - old_value

    def obtain_link(self, ynd):
        response = ynd.get_download_link(self.remote)
        if not response["success"]:
            return None

        return response["data"]["href"]
