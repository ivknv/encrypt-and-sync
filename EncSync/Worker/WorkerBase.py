#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time

from ..Event.EventHandler import EventHandler

if sys.platform.startswith("win"):
    DEFAULT_JOIN_INTERVAL = 1
else:
    DEFAULT_JOIN_INTERVAL = None

class WorkerBase(EventHandler):
    def __init__(self, parent=None):
        EventHandler.__init__(self)

        self.parent = parent
        self.stopped = False

        self.add_event("started")
        self.add_event("stopping")
        self.add_event("finished")
        self.add_event("worker_started")
        self.add_event("worker_finished")

        self.retval = None

    def get_info(self):
        return {}

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

    def actual_join(self, timeout=None):
        raise NotImplementedError

    def join(self, timeout=None, interval=None):
        if interval is None:
            interval = DEFAULT_JOIN_INTERVAL

        if interval is None:
            self.actual_join(timeout)
        elif timeout is None:
            while self.is_alive():
                self.actual_join(interval)
        else:
            interval = min(interval, timeout)

            while self.is_alive() and timeout > 0.0:
                last_time = time.time()
                self.actual_join(interval)
                timeout -= time.time() - last_time

    def is_alive(self):
        raise NotImplementedError

    def start_if_not_alive(self):
        if not self.is_alive():
            self.start()

    def add_worker(self, worker):
        raise NotImplementedError

    def get_worker_list(self):
        raise NotImplementedError

    def join_worker(self, worker, timeout=None, interval=None):
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

    def join_workers(self, timeout=None, each_timeout=None, interval=None):
        workers = self.get_worker_list()

        if timeout is not None:
            if each_timeout is None:
                each_timeout = timeout
            else:
                each_timeout = min(each_timeout, timeout)

        while len(workers) and (timeout is None or timeout > 0):
            for worker in workers:
                t = time.time()

                self.join_worker(worker, each_timeout, interval)

                dt = time.time() - t

                if timeout is not None:
                    timeout -= dt
            workers = self.get_worker_list()

    def stop_workers(self):
        for worker in self.get_worker_list():
            worker.stop()

    def full_stop(self, timeout=None, each_timeout=None, interval=None):
        self.stop()

        last_time = time.time()

        while len(self.get_worker_list()):
            self.stop_workers()
            self.join_workers(timeout, each_timeout, interval)

        if timeout is not None:
            timeout -= time.time() - last_time

        self.join(timeout, interval)
