# -*- coding: utf-8 -*-

from ..LogReceiver import LogReceiver
from ..Worker import Worker
from .Logging import logger

__all__ = ["DuplicateRemoverWorker"]

COMMIT_INTERVAL = 7.5 * 60 # Seconds

class DuplicateRemoverWorker(Worker):
    def __init__(self, parent):
        Worker.__init__(self, parent)

        self.target = parent.cur_target
        self.cur_task = None

        self.add_event("next_task")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def stop_condition(self):
        if self.stopped:
            return True

        if self.target is not None:
            return self.target.status not in (None, "pending")

        return False

    def work(self):
        while not self.stop_condition():
            self.cur_task = self.target.get_next_task()

            if self.cur_task is None:
                break

            if self.stop_condition():
                break

            try:
                self.emit_event("next_task", self.cur_task)
                self.cur_task.complete(self)
            except Exception as e:
                self.emit_event("error", e)
                self.cur_task.status = "failed"
