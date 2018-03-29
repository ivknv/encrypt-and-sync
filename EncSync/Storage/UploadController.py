# -*- coding: utf-8 -*-

from ..Event.Emitter import Emitter

__all__ = ["UploadController"]

class UploadController(Emitter):
    """
        Events: uploaded_changed
    """

    def __init__(self, in_file, limit=float("inf")):
        Emitter.__init__(self)

        self.in_file = in_file
        self.limit = limit
        self._uploaded = 0
        self.stopped = False

    @property
    def uploaded(self):
        return self._uploaded

    @uploaded.setter
    def uploaded(self, value):
        self._uploaded = value

        self.emit_event("uploaded_changed", value)

    def stop(self):
        self.stopped = True

    def work(self):
        raise NotImplementedError
