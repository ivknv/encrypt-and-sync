#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import reduce

from .Logging import logger
from ..Worker import Waiter
from ..Scannable import scan_files
from ..LogReceiver import LogReceiver
from .. import Paths

__all__ = ["DecryptedScanWorker", "AsyncDecryptedScanWorker",
           "EncryptedScanWorker", "AsyncEncryptedScanWorker"]

class ScanWorker(Waiter):
    def __init__(self, parent, target):
        Waiter.__init__(self, parent)

        self.encsync = parent.encsync

        self.cur_target = target
        self.cur_path = None

        self.flist = parent.shared_flist
        self.duplist = parent.shared_duplist

        self.add_event("next_node")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def insert_scannable(self, scannable):
        self.cur_path = scannable.path

        if self.stop_condition():
            return False

        self.flist.insert_node(scannable.to_node())

        return True

    def do_scan(self, task):
        raise NotImplementedError

    def get_next_task(self):
        return self.parent.get_next_task()

    def stop_condition(self):
        target = self.cur_target
        ptarget = self.parent.cur_target

        if self.stopped or self.parent.stopped:
            return True

        if target is not None and target.status != "pending":
            return True

        if ptarget is not None and ptarget.status != "pending":
            return True

        return False

    def handle_task(self, task):
        try:
            if self.stop_condition():
                return False

            handle_more = self.do_scan(task)
            self.cur_path = None

            if self.stop_condition():
                return False

            return handle_more
        except BaseException as e:
            self.emit_event("error", e)
            self.cur_target.change_status("failed")
            task.change_status("failed")
            self.stop()

            return False

    def after_work(self):
        self.cur_path = None
        self.cur_target = None

class DecryptedScanWorker(ScanWorker):
    def get_info(self):
        if self.cur_target is None:
            return {}

        return {"operation": "%s scan" % (self.cur_target.storage.name,),
                "path": self.cur_path}

    def do_scan(self, task):
        assert(not (self.cur_target.encrypted or self.cur_target.storage.parallelizable))

        scannable = task.scannable

        task.change_status("pending")

        if self.cur_target.storage.name == "local":
            allowed_paths = self.encsync.allowed_paths
        else:
            allowed_paths = None

        files = scan_files(scannable, allowed_paths)

        for s, n in files:
            self.cur_path = n["path"]

            self.emit_event("next_node", s)

            if self.stop_condition():
                return False

            if n["type"] is not None:
                self.flist.insert_node(n)

        task.change_status("finished")

        return False

class AsyncDecryptedScanWorker(ScanWorker):
    def get_info(self):
        if self.cur_target is None:
            return {}

        return {"operation": "%s scan" % (self.cur_target.storage.name,),
                "path": self.cur_path}

    def do_scan(self, task):
        assert(not self.cur_target.encrypted and self.cur_target.storage.parallelizable)

        scannable = task.scannable

        task.change_status("pending")

        self.cur_path = scannable.path

        if self.cur_target.storage.name == "local":
            allowed_paths = self.encsync.allowed_paths
        else:
            allowed_paths = None

        scan_result = scannable.scan(allowed_paths)

        for s in scan_result["f"] + scan_result["d"]:
            self.emit_event("next_node", s)

            if not self.insert_scannable(s):
                return False

            if s.type == "d":
                self.parent.add_task(s)

        del scan_result

        task.change_status("finished")

        return True

class EncryptedScanWorker(ScanWorker):
    def get_info(self):
        if self.cur_target is None:
            return {}

        return {"operation": "encrypted %s scan" % (self.cur_target.storage.name,),
                "path": self.cur_path}

    def do_scan(self, task):
        assert(self.cur_target.encrypted and not self.cur_target.storage.parallelizable)

        to_scan = [task.scannable]

        task.change_status("pending")

        if self.cur_target.storage.name == "local":
            allowed_paths = self.encsync.allowed_paths
        else:
            allowed_paths = None

        while not self.stop_condition():
            try:
                scannable = to_scan.pop(0)
            except IndexError:
                break

            self.cur_path = scannable.path

            scan_result = scannable.scan(allowed_paths)

            scannables = {}

            for s in scan_result["f"] + scan_result["d"]:
                if self.stop_condition():
                    return False

                self.emit_event("next_node", s)
                path = Paths.dir_denormalize(s.path)
                scannables.setdefault(path, [])
                scannables[path].append(s)

            del scan_result

            for i in scannables.values():
                original = reduce(lambda x, y: x if x.modified > y.modified else y, i)

                i.remove(original)

                if i:
                    task.emit_event("duplicates_found", [original] + i)
                    self.cur_target.emit_event("duplicates_found", [original] + i)

                    for s in i:
                        self.duplist.insert(s.type, s.IVs, s.path)

                if not self.insert_scannable(original):
                    return False

                if original.type == "d":
                    to_scan.append(original)

        if self.stop_condition():
            return False

        task.change_status("finished")

        return True

class AsyncEncryptedScanWorker(ScanWorker):
    def get_info(self):
        if self.cur_target is None:
            return {}

        return {"operation": "encrypted %s scan" % (self.cur_target.storage.name,),
                "path": self.cur_path}

    def do_scan(self, task):
        assert(self.cur_target.encrypted and self.cur_target.storage.parallelizable)

        scannable = task.scannable

        task.change_status("pending")

        if self.cur_target.storage.name == "local":
            allowed_paths = self.encsync.allowed_paths
        else:
            allowed_paths = None

        self.cur_path = scannable.path

        scan_result = scannable.scan(allowed_paths)

        scannables = {}

        for s in scan_result["f"] + scan_result["d"]:
            if self.stop_condition():
                return False
            self.emit_event("next_node", s)
            path = Paths.dir_denormalize(s.path)
            scannables.setdefault(path, [])
            scannables[path].append(s)

        del scan_result

        for i in scannables.values():
            original = reduce(lambda x, y: x if x.modified > y.modified else y, i)

            i.remove(original)

            if i:
                task.emit_event("duplicates_found", [original] + i)
                self.cur_target.emit_event("duplicates_found", [original] + i)

                for s in i:
                    self.duplist.insert(s.type, s.IVs, s.path)

            if not self.insert_scannable(original):
                return False

            if original.type == "d":
                self.parent.add_task(original)

        if self.stop_condition():
            return False

        task.change_status("finished")

        return True
