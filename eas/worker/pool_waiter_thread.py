# -*- coding: utf-8 -*-

from .mixins import PoolWaiterMixin
from .waiter_thread import WaiterThread

__all__ = ["PoolWaiterThread"]

class PoolWaiterThread(PoolWaiterMixin, WaiterThread):
    def __init__(self, daemon=None):
        WaiterThread.__init__(self, daemon)

        self._pool = None
