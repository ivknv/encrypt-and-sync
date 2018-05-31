# -*- coding: utf-8 -*-

from .logging import logger, WorkerFailLogReceiver
from ..worker import PoolWorkerThread
from ..log_receiver import LogReceiver

__all__ = ["SyncWorker"]

class SyncWorker(PoolWorkerThread):
    """
        Events: next_task, error
    """

    def __init__(self, synchronizer):
        self._stopped = False

        PoolWorkerThread.__init__(self)

        self.cur_task = None
        self.synchronizer = synchronizer

        self.add_receiver(LogReceiver(logger))
        self.add_receiver(WorkerFailLogReceiver())

    def get_info(self):
        return {}

    @property
    def stopped(self):
        return self._stopped or self.synchronizer.stopped

    @stopped.setter
    def stopped(self, value):
        self._stopped = value

    def stop(self):
        super().stop()

        # Intentional assignment for thread safety
        task = self.cur_task

        if task is not None:
            target = task.parent

            if target is not None:
                target.stop()

            task.stop()

    def handle_task(self, task):
        try:
            self.cur_task = task

            if self.stopped:
                return False

            self.emit_event("next_task", task)

            if task.status not in (None, "pending"):
                return

            task.run()

            self.cur_task = None
        except Exception as e:
            self.emit_event("error", e)
            task.status = "failed"
        finally:
            self.cur_task = None
