# -*- coding: utf-8 -*-

import threading
import sys

from .worker import Worker

__all__ = ["WorkerThread", "get_current_worker", "get_main_worker"]

DEFAULT_DAEMON = sys.platform.startswith("win")

class WorkerThread(Worker):
    _workers = {}

    def __init__(self, daemon=None):
        Worker.__init__(self)

        if daemon is None:
            daemon = DEFAULT_DAEMON

        self.daemon = daemon
        self.thread = None

    def run(self):
        try:
            WorkerThread._workers[self.ident] = self

            super().run()
        finally:
            WorkerThread._workers.pop(self.ident, None)

    def start(self):
        if self.thread is None or not self.thread.is_alive() and self.thread.ident is not None:
            self.thread = threading.Thread(target=self.run, daemon=self.daemon)

        self.thread.start()

    def actual_join(self, timeout=None):
        if self.thread is not None:
            self.thread.join(timeout)

    def is_alive(self):
        return self.thread is not None and self.thread.is_alive()

    @property
    def ident(self):
        if self.thread is None:
            return None
        return self.thread.ident

def get_current_worker():
    ident = threading.get_ident()

    try:
        return WorkerThread._workers[ident]
    except KeyError:
        cur_thread = threading.current_thread()
        cur_worker = WorkerThread(cur_thread.daemon)
        cur_worker.thread = cur_thread

        WorkerThread._workers[ident] = cur_worker

        return cur_worker

def get_main_worker():
    main_thread = threading.main_thread()
    ident = main_thread.ident

    try:
        return WorkerThread._workers[ident]
    except KeyError:
        main_worker = WorkerThread(main_thread.daemon)
        main_worker.thread = main_thread

        WorkerThread._workers[ident] = main_worker

        return main_worker

    try:
        return WorkerThread._workers[ident]
    except KeyError:
        cur_thread = threading.current_thread()
        cur_worker = WorkerThread(cur_thread.daemon)
        cur_worker.thread = cur_thread

        WorkerThread._workers[ident] = cur_worker

        return cur_worker
