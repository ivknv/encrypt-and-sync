# -*- coding: utf-8 -*-

from ..log_receiver import LogReceiver
from ..worker import PoolWorkerThread
from .logging import logger

__all__ = ["DuplicateRemoverWorker"]

class DuplicateRemoverWorker(PoolWorkerThread):
    """
        Events: next_task, error
    """

    def __init__(self, duprem):
        PoolWorkerThread.__init__(self)

        self.cur_task = None
        self.duprem = duprem

        self.add_receiver(LogReceiver(logger))

    def stop(self):
        super().stop()

        # Intentional assignment for thread safety
        task = self.cur_task

        if task is not None:
            task.stop()

    def handle_task(self, task):
        self.cur_task = task

        if self.stopped:
            return False

        try:
            self.emit_event("next_task", task)
            task.run()
        except Exception as e:
            self.emit_event("error", e)
            task.status = "failed"
        finally:
            self.cur_task = None
