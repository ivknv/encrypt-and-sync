# -*- coding: utf-8 -*-

from ..LogReceiver import LogReceiver
from ..Worker import Worker
from .Logging import logger

__all__ = ["DuplicateRemoverWorker"]

class DuplicateRemoverWorker(Worker):
    """
        Events: next_task, error
    """

    def __init__(self, parent):
        Worker.__init__(self, parent)

        self.target = parent.cur_target
        self.cur_task = None

        self.add_receiver(LogReceiver(logger))

    def stop_condition(self):
        return self.stopped or self.parent.stopped

    def stop(self):
        Worker.stop(self)

        # Intentional assignment for thread safety
        task = self.cur_task

        if task is not None:
            task.stop()

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
