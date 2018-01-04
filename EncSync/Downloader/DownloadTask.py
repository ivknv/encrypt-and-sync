#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..Task import Task

__all__ = ["DownloadTask"]

class DownloadTask(Task):
    def __init__(self):
        Task.__init__(self)

        self.type = None
        self.src = None
        self.dst = None
        self.src_path = ""
        self.dst_path = ""
        self.size = 0
        self.modified = 0
        self._downloaded = 0
        self._uploaded = 0
        self.total_children = 0

        self.add_event("downloaded_changed")
        self.add_event("uploaded_changed")

    @property
    def downloaded(self):
        return self._downloaded

    @downloaded.setter
    def downloaded(self, value):
        old_value = self._downloaded
        self._downloaded = value

        if old_value != value:
            self.emit_event("downloaded_changed")

            if self.parent is not None:
                self.parent.downloaded += value - old_value

    @property
    def uploaded(self):
        return self._uploaded

    @uploaded.setter
    def uploaded(self, value):
        old_value = self._uploaded
        self._uploaded = value

        if old_value != value:
            self.emit_event("uploaded_changed")
