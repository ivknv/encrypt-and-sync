#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import threading
import os
import time

DEFAULT_FETCH_SIZE = 1000

class DBResult(dict):
    def is_ready(self):
        return self["event"].is_set()

    def wait(self):
        self["event"].wait()

    def get_result(self):
        self.wait()

        if self["exception"] is not None:
            raise self["exception"]

        return self["result"]

def get_queue_result(func):
    def g(*args, wait=True, **kwargs):
        r = func(*args, **kwargs)

        if wait:
            return r.get_result()
        else:
            return r

    return g

class Connection(object):
    def __init__(self, cdb, *args, **kwargs):
        self.cdb = cdb
        self.conn = sqlite3.connect(cdb.path, *args, check_same_thread=False, **kwargs)
        self.cur = self.conn.cursor()

        self._closed = False
        self._using_with = False
        self._with_lock = threading.Lock()
        self._with_thread_id = None
        self._with_count = 0

        self.last_commit = time.time()

        cdb.inc_connection_count()

    def __enter__(self):
        thread_id = threading.get_ident()

        if thread_id != self._with_thread_id:
            self._with_lock.acquire()
            self.cdb.queue_add_lock.acquire()
            self._with_thread_id = thread_id

        self._using_with = True
        self._with_count += 1

    def time_since_last_commit(self):
        return time.time() - self.last_commit

    def __exit__(self, *args, **kwargs):
        self._with_count -= 1

        if self._with_count == 0:
            self._with_lock.release()
            self.cdb.queue_add_lock.release()
            self._with_thread_id = None
            self._using_with = False

    def __del__(self):
        if not self._closed:
            self.cdb.dec_connection_count()

    @get_queue_result
    def add_to_queue(self, func, args, kwargs):
        thread_id = threading.get_ident()

        if self._using_with and thread_id == self._with_thread_id:
            f = self.cdb._add_to_queue
        else:
            f = self.cdb.add_to_queue

        return f(self.conn, func, args, kwargs)

    def begin_transaction(self, transaction_type=None):
        if transaction_type is None:
            transaction_type = ""

        allowed_types = {"", "deferred", "immediate", "exclusive"}

        assert(transaction_type.lower() in allowed_types)

        return self.execute("BEGIN {} TRANSACTION".format(transaction_type))

    def seamless_commit(self):
        with self:
            if not self.conn.in_transaction:
                return

            self.commit()
            self.begin_transaction("IMMEDIATE")

    def embed(self, func, *args, **kwargs):
        with self.conn:
            return self.add_to_queue(self._embed, (func,) + args, kwargs)

    def _embed(self, func, *args, **kwargs):
        assert(not self.cdb._embedded_mode)

        try:
            self.cdb._embedded_mode = True

            return func(*args, **kwargs)
        finally:
            self.cdb._embedded_mode = False

    def _execute(self, *args, **kwargs):
        self.cur.execute(*args, **kwargs)

    def execute(self, *args, **kwargs):
        return self.add_to_queue(self._execute, args, kwargs)

    def _commit(self):
        self.conn.commit()
        self.last_commit = time.time()

    def commit(self):
        return self.add_to_queue(self._commit, tuple(), dict())

    def rollback(self):
        return self.add_to_queue(self.conn.rollback, tuple(), dict())

    def _close(self):
        if self._closed:
            return

        self.cur.close()
        self.conn.close()
        self._closed = True
        self.cdb.dec_connection_count()

    def close(self):
        return self.add_to_queue(self._close, tuple(), dict())

    def fetchone(self):
        return self.add_to_queue(self.cur.fetchone, tuple(), dict())

    def fetchmany(self, size=DEFAULT_FETCH_SIZE):
        return self.add_to_queue(self.cur.fetchmany, (size,), {})

    def genfetch(self, *args, **kwargs):
        r = self.fetchmany(*args, **kwargs)
        while len(r):
            for i in r:
                yield i
            r = self.fetchmany(*args, **kwargs)

class CDB(object):
    databases = {}

    def __init__(self, path):
        self.path = path

        self.cur_conn = None

        self.queue = []
        self.secondary_queue = []

        self.queue_add_lock = threading.Lock()
        self.queue_pop_lock = threading.Lock()

        self.dirty = threading.Event()
        self.stopped = False
        self.thread = None
        self.n_connections = 0
        self.n_connections_lock = threading.Lock()

        self.queue_limit = 50

        self.queue_busy = threading.Event()
        self.queue_busy.set()

        self._embedded_mode = False

    def inc_connection_count(self):
        with self.n_connections_lock:
            self.n_connections += 1
            self.dirty.set()

    def dec_connection_count(self):
        with self.n_connections_lock:
            self.n_connections -= 1
            self.dirty.set()

    def add_to_queue(self, conn, func, args, kwargs):
        with self.queue_add_lock:
            return self._add_to_queue(conn, func, args, kwargs)

    def _add_to_queue(self, conn, func, args, kwargs):
        r = DBResult({"conn": conn,
                      "func": func,
                      "args": args,
                      "kwargs": kwargs,
                      "event": threading.Event(),
                      "result": None,
                      "exception": None})
        
        if self._embedded_mode:
            self.execute(r)
            return r

        self.queue_busy.wait()
        with self.queue_pop_lock:
            self.queue.append(r)
            self.dirty.set()

            self.update_queue_busy()

            return r

    def update_queue_busy(self):
        if len(self.queue) + len(self.secondary_queue) > self.queue_limit:
            self.queue_busy.clear()
        else:
            self.queue_busy.set()

    def merge_queues(self):
        with self.queue_pop_lock:
            self.secondary_queue.extend(self.queue)

            self.queue.clear()

            # Swap queues
            self.queue, self.secondary_queue = self.secondary_queue, self.queue

            if len(self.queue):
                self.dirty.set()

    def stop(self):
        self.stopped = True
        self.dirty.set()

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        return self.thread

    def join(self):
        if self.thread is not None:
            self.thread.join()

    def is_alive(self):
        return self.thread.is_alive() if self.thread is not None else False

    def execute(self, r):
        conn, func, args, kwargs = r["conn"], r["func"], r["args"], r["kwargs"]
        event = r["event"]

        if self.cur_conn is not conn and self.cur_conn is not None:
            assert(self.cur_conn.in_transaction)
            assert(not conn.in_transaction)

            self.secondary_queue.append(r)
            self.update_queue_busy()

            return

        self.cur_conn = conn

        in_transaction_before = self.cur_conn.in_transaction

        try:
            r["result"] = func(*args, **kwargs)
        except Exception as e:
            r["exception"] = e

        try:
            if not self.cur_conn.in_transaction:
                self.cur_conn = None
        except sqlite3.ProgrammingError:
            self.cur_conn = None

        event.set()

    def stop_condition(self):
        return self.n_connections == 0 or self.stopped

    def run(self):
        try:
            self.stopped = False
            self.dirty.set()

            while not self.stop_condition():
                self.dirty.wait()

                if self.stop_condition():
                    break

                if self.cur_conn is None:
                    self.merge_queues()

                with self.queue_pop_lock:
                    if self.stop_condition():
                        break

                    if len(self.queue) == 0:
                        self.dirty.clear()
                        continue

                    r = self.queue.pop(0)

                    self.update_queue_busy()

                self.execute(r)
        finally:
            self.thread = None

def connect(path, *args, **kwargs):
    path = os.path.abspath(os.path.expanduser(path))
    cdb = CDB.databases.get(path, None)

    if cdb is None:
        cdb = CDB(path)
        CDB.databases[path] = cdb

    c = Connection(cdb, *args, **kwargs)

    if cdb.thread is None:
        cdb.start()

    return c

def get(path, default=None):
    return CDB.databases.get(path, default)

def stop(path):
    get(path).stop()

def stop_all():
    for i in CDB.databases.values():
        i.stop()
