#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
from .Event import Emitter, Receiver
from .Worker import Worker

class DispatcherError(BaseException):
    pass

class DuplicateStageError(DispatcherError):
    def __init__(self, name):
        self.name = name

        msg = "Stage {} already exists".format(repr(name))

        DispatcherError.__init__(self, msg)

class UnknownStageError(DispatcherError):
    def __init__(self, name):
        self.name = name

        msg = "Unknown stage {}".format(repr(name))

        DispatcherError.__init__(self, msg)

class Dispatcher(Worker):
    def __init__(self, parent=None, daemon=False):
        Worker.__init__(self, parent, daemon=daemon)

        self.workers = {}
        self.workers_lock = threading.Lock()

    def add_worker(self, worker):
        with self.workers_lock:
            self.workers[worker.ident] = worker

        return worker

    def start_worker(self, worker_class, *args, **kwargs):
        worker = worker_class(*args, **kwargs)
        worker.start()
        self.add_worker(worker)

        return worker

    def start_workers(self, n_workers, worker_class, *args, **kwargs):
        for i in range(n_workers):
            self.start_worker(worker_class, *args, **kwargs)

    def get_worker_list(self):
        with self.workers_lock:
            return list(self.workers.values())

    def join_workers(self):
        workers = self.get_worker_list()

        while len(workers):
            for worker in workers:
                worker.join()
                with self.workers_lock:
                    self.workers.pop(worker.ident, None)
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

class StagedDispatcher(Dispatcher):
    def __init__(self, parent=None, daemon=False):
        Dispatcher.__init__(self, parent, daemon)

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
