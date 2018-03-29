#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Logging import logger
from ..Worker import Worker
from ..LogReceiver import LogReceiver

__all__ = ["DownloaderWorker"]

class DownloaderWorker(Worker):
    """
        Events: next_task, error
    """

    def __init__(self, downloader):
        Worker.__init__(self, downloader)
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

    def get_info(self):
        if self.cur_task is not None:
            try:
                progress = float(self.cur_task.downloaded) / self.cur_task.size
            except ZeroDivisionError:
                progress = 1.0

            return {"operation": "downloading",
                    "path":      self.cur_task.src_path,
                    "progress":  progress}

        return {"operation": "downloading",
                "progress":  0.0}

    def work(self):
        while not self.stop_condition():
            try:
                if self.parent.cur_target is not None:
                    self.cur_task = self.parent.cur_target.get_next_task()

                if self.cur_task is None:
                    break

                self.emit_event("next_task", self.cur_task)

                self.cur_task.complete(self)
            except Exception as e:
                self.emit_event("error", e)

                if self.cur_task is not None:
                    self.cur_task.status = "failed"
            finally:
                self.cur_task = None
