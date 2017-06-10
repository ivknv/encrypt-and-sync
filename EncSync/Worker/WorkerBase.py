#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from ..Event.EventHandler import EventHandler

class WorkerBase(EventHandler):
    def __init__(self, parent=None):
        EventHandler.__init__(self)

        self.parent = parent
        self.stopped = False

        # Synchronization lock
        if parent is not None:
            self.sync_lock = parent.get_sync_lock()
        else:
            self.sync_lock = threading.Lock()

        self.add_event("started")
        self.add_event("stopping")
        self.add_event("finished")
        self.add_event("worker_started")
        self.add_event("worker_finished")

        self.retval = None

    def get_info(self):
        return {}

    def get_sync_lock(self):
        return self.sync_lock

    def stop(self):
        self.stopped = True
        self.emit_event("stopping")

        for worker in self.get_worker_list():
            worker.stop()

    def before_work(self):
        pass

    def work(self):
        pass

    def after_work(self):
        pass

    def run(self):
        self.emit_event("started")

        try:
            self.before_work()

            try:
                self.retval = self.work()
            finally:
                self.after_work()
        finally:
            self.emit_event("finished")

            if self.parent is not None:
                self.parent.emit_event("worker_finished", self)

    def start(self):
        raise NotImplementedError

    def join(self):
        raise NotImplementedError

    def is_alive(self):
        raise NotImplementedError

    def start_if_not_alive(self):
        if not self.is_alive():
            self.start()

    def add_worker(self, worker):
        raise NotImplementedError

    def get_worker_list(self):
        raise NotImplementedError

    def join_worker(self, worker):
        raise NotImplementedError

    def get_num_alive(self):
        return sum(1 for i in self.get_worker_list() if i.is_alive())

    def start_worker(self, worker_class, *args, **kwargs):
        worker = worker_class(*args, **kwargs)
        worker.start()
        self.add_worker(worker)

        self.emit_event("worker_started", worker)

        return worker

    def start_workers(self, n_workers, worker_class, *args, **kwargs):
        for i in range(n_workers):
            self.start_worker(worker_class, *args, **kwargs)

    def join_workers(self):
        workers = self.get_worker_list()

        while len(workers):
            for worker in workers:
                self.join_worker(worker)
            workers = self.get_worker_list()

    def stop_workers(self):
        for worker in self.get_worker_list():
            worker.stop()

    def full_stop(self):
        self.stop()

        while len(self.get_worker_list()):
            self.stop_workers()
            self.join_workers()

        self.join()
