# -*- coding: utf-8 -*-

from ..Event.Emitter import Emitter

__all__ = ["DownloadController"]

class DownloadController(Emitter):
    def __init__(self, out_file, limit=float("inf")):
        Emitter.__init__(self)

        self.out_file = out_file
        self.limit = limit
        self._downloaded = 0
        self.stopped = False

        self.add_event("downloaded_changed")

    @property
    def downloaded(self):
        return self._downloaded

    @downloaded.setter
    def downloaded(self, value):
        self._downloaded = value

        self.emit_event("downloaded_changed", value)

    def stop(self):
        self.stopped = True

    def work(self):
        raise NotImplementedError