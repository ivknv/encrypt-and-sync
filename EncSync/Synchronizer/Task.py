# -*- coding: utf-8 -*-

from ..Task import Task

__all__ = ["SyncTask"]

class SyncTask(Task):
    def __init__(self):
        Task.__init__(self)

        self.task_type = None # "new", "update", "rm" or "rmdup"
        self.type = None # "f" or "d"
        self.path = None
        self.size = 0
        self._uploaded = 0
        self._downloaded = 0

        self.add_event("uploaded_changed")
        self.add_event("downloaded_changed")
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

    @property
    def downloaded(self):
        return self._downloaded

    @downloaded.setter
    def downloaded(self, value):
        old_value = self._downloaded
        self._downloaded = value

        if value != old_value:
            self.emit_event("downloaded_changed")
