# -*- coding: utf-8 -*-

from ..LogReceiver import LogReceiver
from ..Worker import Worker
from .Logging import logger

__all__ = ["DuplicateRemoverWorker"]

COMMIT_INTERVAL = 7.5 * 60 # Seconds

class DuplicateRemoverWorker(Worker):
    def __init__(self, parent):
        Worker.__init__(self, parent)

        self.duplist = parent.shared_duplist
        self.target = parent.cur_target
        self.encsync = parent.encsync
        self.cur_task = None

        self.add_event("next_task")
        self.add_event("error")
        self.add_event("autocommit_started")
        self.add_event("autocommit_failed")
        self.add_event("autocommit_finished")

        self.add_receiver(LogReceiver(logger))

    def autocommit(self):
        if self.duplist.time_since_last_commit() >= COMMIT_INTERVAL:
            try:
                self.emit_event("autocommit_started", self.duplist)
                self.duplist.seamless_commit()
                self.emit_event("autocommit_finished", self.duplist)
            except Exception as e:
                self.emit_event("autocommit_failed", self.duplist)
                raise e

    def stop_condition(self):
        if self.target is not None:
            return self.target.status != "pending" or self.stopped

        return self.stopped

    def work(self):
        while not self.stop_condition():
            self.cur_task = self.parent.get_next_task()

            if self.cur_task is None:
                break

            if self.stop_condition():
                break

            try:
                task = self.cur_task

                task.status = "pending"

                self.emit_event("next_task", task)

                encoding = task.filename_encoding
                encpath = self.encsync.encrypt_path(task.path, task.prefix,
                                                    IVs=task.ivs,
                                                    filename_encoding=encoding)[0]

                try:
                    task.storage.remove(encpath)
                except FileNotFoundError:
                    pass

                self.duplist.remove(task.ivs, task.path)
                self.autocommit()

                task.status = "finished"
            except Exception as e:
                self.emit_event("error", e)
                self.cur_task.status = "failed"
