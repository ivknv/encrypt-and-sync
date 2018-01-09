#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Logging import logger
from .Tasks import UploadTask
from ..Worker import Worker
from ..LogReceiver import LogReceiver

__all__ = ["SyncWorker"]

class SyncWorker(Worker):
    def __init__(self, parent):
        Worker.__init__(self, parent)

        self.encsync = parent.encsync
        self.speed_limit = parent.speed_limit
        self.cur_task = None

        self.add_event("next_task")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def get_info(self):
        return {}

    def stop(self):
        Worker.stop(self)

        if self.cur_task is not None and isinstance(self.cur_task, UploadTask):
            if self.cur_task.upload_controller is not None:
                self.cur_task.upload_controller.stop()

            if self.cur_task.download_controller is not None:
                self.cur_task.download_controller.stop()

    def stop_condition(self):
        if self.stopped or self.parent.stopped:
            return True

        return self.cur_task is not None and self.cur_task.stop_condition()

    def work(self):
        while not self.stop_condition():
            try:
                if self.stop_condition():
                    break

                task = self.parent.cur_target.get_next_task()
                self.cur_task = task

                if task is None or self.stop_condition():
                    break

                self.emit_event("next_task", task)

                if task.status not in (None, "pending"):
                    continue

                task.complete(self)

                self.cur_task = None
            except Exception as e:
                self.emit_event("error", e)
                if self.cur_task is not None:
                    self.cur_task.status = "failed"

    def after_work(self):
        self.cur_task = None
