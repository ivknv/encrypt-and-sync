# -*- coding: utf-8 -*-

from .logging import logger
from ..worker import PoolWorkerThread
from ..log_receiver import LogReceiver

__all__ = ["DownloaderWorker"]

class DownloaderWorker(PoolWorkerThread):
    """
        Events: next_task, error
    """

    def __init__(self, downloader):
        super().__init__()

        self.cur_task = None
        self.downloader = downloader

        self.add_receiver(LogReceiver(logger))

    def stop(self):
        super().stop()

        # Intentional assignment for thread safety
        task = self.cur_task

        if task is not None:
            task.stop()

    def get_info(self):
        if self.cur_task is None:
            return {"operation": "downloading",
                    "progress":  0.0}

        try:
            progress = float(self.cur_task.downloaded) / self.cur_task.size
        except ZeroDivisionError:
            progress = 1.0

        return {"operation": "downloading",
                "path":      self.cur_task.src_path,
                "progress":  progress}

    def handle_task(self, task):
        try:
            if self.stopped:
                return False

            self.cur_task = task
            self.emit_event("next_task", task)

            task.run()
        except Exception as e:
            self.emit_event("error", e)

            task.status = "failed"
        finally:
            self.cur_task = None
