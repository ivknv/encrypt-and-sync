# -*- coding: utf-8 -*-

import collections
import threading
import time
import weakref

from ..events import Emitter
from .worker import Worker

__all__ = ["WorkerPool"]

class WorkerPool(Emitter):
    """
        Events: spawn
    """

    def __init__(self, queue=None):
        if queue is None:
            queue = collections.deque()

        Emitter.__init__(self)

        self._workers = []
        self._worker_lock = threading.RLock()
        self.queue = queue

    def clear(self):
        with self._worker_lock:
            if any(True for i in self._workers if i.is_alive()):
                raise RuntimeError("Attempt to clear a running worker pool")

            workers = list(self._workers)

            self._workers.clear()

            for worker in workers:
                worker._pool = None

    def add_task(self, task):
        self.queue.append(task)

        with self._worker_lock:
            for worker in self._workers:
                if worker.is_idle():
                    worker.set_dirty()

    def get_task(self):
        if isinstance(self.queue, collections.Iterator):
            return next(self.queue)

        try:
            if hasattr(self.queue, "popleft"):
                return self.queue.popleft()

            return self.queue.pop(0)
        except IndexError:
            raise StopIteration

    def spawn(self, worker_or_class, *args, **kwargs):
        if isinstance(worker_or_class, Worker):
            worker = worker_or_class
        else:
            worker = worker_or_class(*args, **kwargs)

        self.add_worker(worker)
        self.emit_event("spawn", worker)

        worker.start()

        return worker

    def spawn_many(self, n, worker_or_class, *args, **kwargs):
        for i in range(n):
            self.spawn(worker_or_class, *args, **kwargs)

    def add_worker(self, worker):
        with self._worker_lock:
            self._workers.append(worker)
            worker._pool = weakref.ref(self)

        return worker

    def add_workers(self, workers):
        with self._worker_lock:
            for worker in workers:
                self._workers.append(worker)

    def add_many_workers(self, n, worker_or_class, *args, **kwargs):
        for i in range(n):
            if isinstance(worker_or_class, Worker):
                worker = worker_or_class
            else:
                worker = worker_or_class(*args, **kwargs)

            self.add_worker(worker)

    def get_worker_list(self):
        with self._worker_lock:
            return list(self._workers)

    def stop(self):
        with self._worker_lock:
            for worker in self._workers:
                worker.stop()

    def join(self, timeout=None, each_timeout=None, interval=None):
        workers = self.get_worker_list()

        if timeout is not None:
            if each_timeout is None:
                each_timeout = timeout
            else:
                each_timeout = min(each_timeout, timeout)

        while timeout is None or timeout > 0:
            alive_workers = [w for w in workers if w.is_alive()]

            if not alive_workers:
                break

            for worker in alive_workers:
                t = time.monotonic()

                worker.join(each_timeout, interval)

                dt = time.monotonic() - t

                if timeout is not None:
                    timeout -= dt
            workers = self.get_worker_list()

    def wait_idle(self, timeout=None):
        workers = self.get_worker_list()

        while any(not w.is_idle() for w in workers) or not workers:
            for worker in workers:
                worker.wait_idle(timeout)

            workers = self.get_worker_list()

    def get_alive(self):
        return [i for i in self.get_worker_list() if i.is_alive()]

    def get_n_alive(self):
        return len(self.get_alive())

    def start(self):
        for worker in self.get_worker_list():
            if not worker.is_alive():
                self.emit_event("spawn", worker)

                worker.start()

    def is_alive(self):
        return any(i.is_alive() for i in self.get_worker_list())
