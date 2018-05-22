# -*- coding: utf-8 -*-

from .mixins import PoolWorkerMixin, SupportsDirtyMixin
from .worker_thread import WorkerThread

__all__ = ["PoolWorkerThread"]

class PoolWorkerThread(PoolWorkerMixin, SupportsDirtyMixin, WorkerThread):
    def __init__(self, daemon=None):
        WorkerThread.__init__(self, daemon)
        SupportsDirtyMixin.__init__(self)

        self._pool = None
