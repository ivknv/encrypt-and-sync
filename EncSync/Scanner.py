#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
from . import SyncList
from .Task import Task

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(name)s-Thread-%(thread)d: %(message)s")

handler = logging.FileHandler("scanner.log")
handler.setFormatter(formatter)

logger.addHandler(handler)

class ScanTask(Task):
    def __init__(self, scan_type=None, path=None):
        Task.__init__(self)
        self.type = scan_type
        self.path = path

class ScannerWorker(threading.Thread):
    def __init__(self, scanner):
        threading.Thread.__init__(self, target=self.work)
        self.scanner = scanner
        self.pool_lock = self.scanner.pool_lock
        self.pool = scanner.pool
        self.encsync = scanner.encsync
        self.stopped = False

    def stop(self):
        self.stopped = True

    def work(self):
        synclist = SyncList.SyncList()
        synclist.create()

        while not self.stopped:
            with self.pool_lock:
                if self.stopped or len(self.pool) == 0:
                    break

                task = self.pool.pop(0)

            if task.status == "suspended":
                continue

            task.change_status("pending")

            if task.type == "local":
                files = SyncList.scan_files(task.path)
                try:
                    with synclist:
                        synclist.remove_local_node_children(task.path)

                        for i in files:    
                            if self.stopped or task.status != "pending":
                                return  
                            synclist.insert_local_node(i)
                        synclist.commit()
                        task.change_status("finished")
                except Exception as e:
                    task.change_status("failed")
                    logger.exception("An error occured")
            elif task.type == "remote":
                files = SyncList.scan_files_ynd(task.path, self.encsync)
                with synclist:
                    synclist.remove_remote_node_children(task.path)

                    try:
                        for i in files:
                            if self.stopped or task.status != "pending":
                                return
                            synclist.insert_remote_node(i)
                        synclist.commit()
                        task.change_status("finished")
                    except:
                        task.change_status("failed")
                        logger.exception("An error occured")

class Scanner(object):
    def __init__(self, encsync, n_workers=2):
        self.encsync = encsync
        self.pool = []
        self.n_workers = n_workers
        self.workers = {}

        self.pool_lock = threading.Lock()
        self.workers_lock = threading.Lock()

    def add_dir(self, scan_type, path):
        task = ScanTask(scan_type, path)

        self.add_task(task)

        return task

    def add_task(self, task):
        with self.pool_lock:
            self.pool.append(task)

    def add_local_dir(self, path):
        return self.add_dir("local", path)

    def add_remote_dir(self, path):
        return self.add_dir("remote", path)

    def get_worker_list(self):
        with self.workers_lock:
            return list(self.workers.values())

    def start(self):
        with self.workers_lock:
            n_running = 0
            for i in list(self.workers.values()):
                if i.is_alive():
                    n_running += 1
                else:
                    self.workers.pop(i.ident, None)

            for i in range(self.n_workers - n_running):
                worker = ScannerWorker(self)
                worker.start()
                self.workers[worker.ident] = worker

    def is_alive(self):
        return any(i.is_alive() for i in self.get_worker_list())

    def stop(self):
        workers = [i for i in self.get_worker_list() if not i.stopped]
        while len(workers):
            for worker in workers:
                worker.stop()
            workers = [i for i in self.get_worker_list() if not i.stopped]

    def join(self):
        workers = self.get_worker_list()
        while len(workers):
            for worker in workers:
                worker.join()
                with self.workers_lock:
                    self.workers.pop(worker.ident, None)
            workers = self.get_worker_list()
