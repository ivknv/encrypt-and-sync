# -*- coding: utf-8 -*-

from .mixins import WaiterMixin, SupportsDirtyMixin
from .worker_thread import WorkerThread

__all__ = ["WaiterThread"]

class WaiterThread(SupportsDirtyMixin, WaiterMixin, WorkerThread):
    def __init__(self, daemon=None):
        WorkerThread.__init__(self, daemon)
        SupportsDirtyMixin.__init__(self)
