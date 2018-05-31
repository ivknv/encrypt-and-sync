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
        self._stopped = False

        PoolWorkerThread.__init__(self)

        self.cur_task = None
        self.duprem = duprem

        self.add_receiver(LogReceiver(logger))

    @property
    def stopped(self):
        return self._stopped or self.duprem.stopped

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
