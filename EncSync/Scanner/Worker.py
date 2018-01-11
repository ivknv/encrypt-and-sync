#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Logging import logger
from ..Worker import Waiter
from ..LogReceiver import LogReceiver

__all__ = ["ScanWorker"]

class ScanWorker(Waiter):
    def __init__(self, parent, target):
        Waiter.__init__(self, parent)

        self.cur_target = target
        self.cur_task = None

        self.flist = target.shared_flist
        self.duplist = target.shared_duplist

        self.add_event("next_node")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def get_info(self):
        if self.cur_target is None:
            return {}

        try:
            storage_name = self.cur_target.storage.name
        except AttributeError:
            return

        try:
            cur_path = self.cur_task.cur_path
        except AttributeError:
            cur_path = None

        return {"operation": "%s scan" % (storage_name,),
                "path": cur_path}

    def get_next_task(self):
        return self.cur_target.get_next_task()

    def add_task(self, task):
        self.cur_target.add_task(task)

    def stop_condition(self):
        return self.stopped or self.parent.stopped

    def stop(self):
        Waiter.stop(self)

        # Intentional assignment for thread safety
        task = self.cur_task

        if task is not None:
            task.stop()

    def handle_task(self, task):
        try:
            if self.stop_condition():
                return False

            self.cur_task = task

            handle_more = task.complete(self)

            self.cur_task = None

            if self.stop_condition():
                return False

            return handle_more
        except Exception as e:
            self.emit_event("error", e)
            task.status = "failed"
            self.cur_target.status = "failed"
            self.stop()

            return False

    def after_work(self):
        self.cur_task = None
        self.cur_target = None
