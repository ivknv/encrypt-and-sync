#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from ..Event.EventHandler import EventHandler
from .Exceptions import UnknownStageError, DuplicateStageError

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

class WorkerProxy(WorkerBase):
    def __init__(self, parent=None):
        WorkerBase.__init__(self, parent)
        self._worker = None

    def setup_worker(self):
        raise NotImplementedError

    @property
    def worker(self):
        if self._worker is None:
            self.setup_worker()

        return self._worker

    @worker.setter
    def worker(self, value):
        self._worker = value

    def start(self):
        if not self.is_alive():
            self.setup_worker()

        self.worker.start()

    def join(self):
        if self.is_alive():
            self.worker.join()

    def is_alive(self):
        return self.worker.is_alive()

    def add_worker(self, worker):
        self._worker.add_worker(worker)

    def get_worker_list(self):
        return self._worker.get_worker_list()

    def join_worker(self, worker):
        if not self._worker.is_alive():
            raise RuntimeError

        self._worker.join_worker(worker)

class Worker(threading.Thread, WorkerBase):
    def __init__(self, parent=None, daemon=False):
        threading.Thread.__init__(self, daemon=daemon)
        WorkerBase.__init__(self, parent)

        self.workers = {}
        self.workers_lock = threading.Lock()

    def add_worker(self, worker):
        with self.workers_lock:
            self.workers[worker.ident] = worker

        return worker

    def join_worker(self, worker):
        worker.join()

        with self.workers_lock:
            self.workers.pop(worker.ident, None)

    def get_worker_list(self):
        with self.workers_lock:
            return list(self.workers.values())

    def run(self):
        WorkerBase.run(self)

class StagedWorker(Worker):
    def __init__(self, parent=None, daemon=False):
        Worker.__init__(self, parent, daemon)

        self.stage = None
        self.available = True

        self.stages = {}

        self.add_event("entered_stage")
        self.add_event("exited_stage")

    def run_stage(self, stage):
        try:
            self.enter_stage(stage)
            self.join_workers()
        finally:
            if self.stage is not None:
                self.exit_stage()

    def add_stage(self, name, on_enter=None, on_exit=None):
        stage = {"name":  name,
                 "enter": on_enter,
                 "exit":  on_exit}

        if name in self.stages:
            raise DuplicateStageError(name)

        self.stages[name] = stage

    def enter_stage(self, name):
        assert(self.stage is None)
        assert(name is not None)

        try:
            self.stage = self.stages[name]
        except KeyError:
            raise UnknownStageError(name)

        self.available = True

        self.emit_event("entered_stage", name)

        enter_callback = self.stage["enter"]

        if enter_callback:
            enter_callback()

    def exit_stage(self):
        assert(self.stage is not None)

        self.available = False

        self.stop_workers()

        exit_callback = self.stage["exit"]

        try:
            if exit_callback:
                exit_callback()
        finally:
            self.emit_event("exited_stage", self.stage)
            self.stage = None
