#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import reduce

from ..Task import Task
from .. import Paths
from ..Scannable import scan_files

__all__ = ["ScanTask", "DecryptedScanTask", "EncryptedScanTask",
           "AsyncDecryptedScanTask", "AsyncDecryptedScanTask"]

class ScanTask(Task):
    def __init__(self, target, scannable=None):
        Task.__init__(self)

        self.parent = target
        self.scannable = scannable

        self.flist = target.shared_flist
        self.duplist = target.shared_duplist
        self.config = target.config
        self.cur_path = None

        self.add_event("interrupt")
        self.add_event("duplicates_found")

    def stop_condition(self, worker):
        if self.stopped or worker.stopped:
            return True

        if self.status not in (None, "pending"):
            return True

        return self.parent.status not in (None, "pending")

class DecryptedScanTask(ScanTask):
    def complete(self, worker):
        if self.stop_condition(worker):
            return False

        target = self.parent

        self.status = "pending"
        allowed_paths = self.config.allowed_paths.get(target.storage.name, [])

        files = scan_files(self.scannable, allowed_paths)

        for s, n in files:
            self.cur_path = n["path"]

            worker.emit_event("next_node", s)

            if self.stop_condition(worker):
                return False

            if n["type"] is not None:
                self.flist.insert_node(n)

        self.status = "finished"

        return False

class EncryptedScanTask(ScanTask):
    def complete(self, worker):
        if self.stop_condition(worker):
            return False

        target = self.parent
        to_scan = [self.scannable]

        self.status = "pending"

        allowed_paths = self.config.allowed_paths(target.storage.name, [])

        while not self.stop_condition(worker):
            try:
                scannable = to_scan.pop(0)
            except IndexError:
                break

            self.cur_path = scannable.path

            scan_result = scannable.scan(allowed_paths)

            scannables = {}

            for s in scan_result["f"] + scan_result["d"]:
                if self.stop_condition(worker):
                    return False

                worker.emit_event("next_node", s)
                path = Paths.dir_denormalize(s.path)
                scannables.setdefault(path, [])
                scannables[path].append(s)

            del scan_result

            for i in scannables.values():
                original = reduce(lambda x, y: x if x.modified > y.modified else y, i)

                i.remove(original)

                if i:
                    self.emit_event("duplicates_found", [original] + i)
                    target.emit_event("duplicates_found", [original] + i)

                    for s in i:
                        self.duplist.insert(s.type, s.IVs, s.path)

                self.cur_path = original.path
                self.flist.insert_node(original.to_node())

                if self.stop_condition(worker):
                    return False

                if original.type == "d":
                    to_scan.append(original)

        if self.stop_condition(worker):
            return False

        self.status = "finished"

        return True

class AsyncDecryptedScanTask(ScanTask):
    def complete(self, worker):
        if self.stop_condition(worker):
            return False

        target = self.parent
        scannable = self.scannable

        self.status = "pending"
        self.cur_path = scannable.path

        allowed_paths = self.config.allowed_paths.get(target.storage.name, [])

        scan_result = scannable.scan(allowed_paths)

        for s in scan_result["f"] + scan_result["d"]:
            worker.emit_event("next_node", s)

            self.cur_path = s.path

            self.flist.insert_node(s.to_node())

            if self.stop_condition(worker):
                return False

            if s.type == "d":
                self.parent.add_task(AsyncDecryptedScanTask(target, s))

        del scan_result

        self.status = "finished"

        return True

class AsyncEncryptedScanTask(ScanTask):
    def complete(self, worker):
        if self.stop_condition(worker):
            return False

        target = self.parent
        scannable = self.scannable
        self.status = "pending"

        allowed_paths = self.config.allowed_paths.get(target.storage.name, [])

        self.cur_path = scannable.path

        scan_result = scannable.scan(allowed_paths)

        scannables = {}

        for s in scan_result["f"] + scan_result["d"]:
            if self.stop_condition(worker):
                return False

            worker.emit_event("next_node", s)

            path = Paths.dir_denormalize(s.path)
            scannables.setdefault(path, [])
            scannables[path].append(s)

        del scan_result

        for i in scannables.values():
            original = reduce(lambda x, y: x if x.modified > y.modified else y, i)

            i.remove(original)

            if i:
                self.emit_event("duplicates_found", [original] + i)
                target.emit_event("duplicates_found", [original] + i)

                for s in i:
                    self.duplist.insert(s.type, s.IVs, s.path)

            self.cur_path = original.path
            self.flist.insert_node(original.to_node())

            if self.stop_condition(worker):
                return False

            if original.type == "d":
                self.parent.add_task(AsyncEncryptedScanTask(target, original))

        if self.stop_condition(worker):
            return False

        self.status = "finished"

        return True
