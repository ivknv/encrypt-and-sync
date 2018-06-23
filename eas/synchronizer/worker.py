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
        PoolWorkerThread.__init__(self)

        self.cur_task = None
        self.synchronizer = synchronizer

        self.add_receiver(LogReceiver(logger))
        self.add_receiver(WorkerFailLogReceiver())

    def get_info(self):
        return {}

    def stop(self):
        super().stop()

        # Intentional assignment for thread safety
        task = self.cur_task

        if task is not None:
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
