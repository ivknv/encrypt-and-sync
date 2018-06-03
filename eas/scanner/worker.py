# -*- coding: utf-8 -*-

from .logging import logger
from ..worker import PoolWaiterThread
from ..log_receiver import LogReceiver

__all__ = ["ScanWorker"]

class ScanWorker(PoolWaiterThread):
    """
        Events: next_node, error
    """

    def __init__(self, scanner):
        self._stopped = False

        PoolWaiterThread.__init__(self)

        self.cur_task = None
        self.scanner = scanner

        self.add_receiver(LogReceiver(logger))

    def get_info(self):
        if self.cur_task is None:
            return {}

        try:
            storage_name = self.cur_task.parent.storage.name
        except AttributeError:
            return

        try:
            cur_path = self.cur_task.cur_path
        except AttributeError:
            cur_path = None

        return {"operation": "%s scan" % (storage_name,),
                "path": cur_path}

    @property
    def stopped(self):
        return self._stopped or self.scanner.stopped

    @stopped.setter
    def stopped(self, value):
        self._stopped = value

    def stop(self):
        super().stop()

        # Intentional assignment for thread safety
        task = self.cur_task

        if task is not None:
            target = task.parent

            if target is not None and not target.stopped:
                target.stop()

            if not task.stopped:
                task.stop()

    def handle_task(self, task):
        try:
            if self.stopped:
                return False

            self.cur_task = task

            handle_more = task.run() is not False

            self.cur_task = None

            if self.stopped:
                return False

            return handle_more
        except Exception as e:
            self.emit_event("error", e)
            task.status = "failed"
            task.parent.status = "failed"
            self.stop()

            return False
        finally:
            self.cur_task = None
