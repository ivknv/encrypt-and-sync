# -*- coding: utf-8 -*-

from functools import reduce

from ..task import Task
from ..scannable import scan_files
from ..worker import get_current_worker
from .. import pathm

__all__ = ["ScanTask", "DecryptedScanTask", "EncryptedScanTask",
           "AsyncDecryptedScanTask", "AsyncDecryptedScanTask"]

class ScanTask(Task):
    """
        Events: interrupt, duplicates_found
    """

    def __init__(self, target, scannable=None):
        Task.__init__(self)

        self.parent = target
        self.scannable = scannable

        self.flist = target.shared_flist
        self.duplist = target.shared_duplist
        self.config = target.config
        self.cur_path = None

    def run(self):
        try:
            return super().run()
        except KeyboardInterrupt:
            return False

class DecryptedScanTask(ScanTask):
    def complete(self):
        if self.stopped:
            return False

        worker = get_current_worker()

        target = self.parent

        self.status = "pending"

        allowed_paths = list(self.config.allowed_paths.get(target.storage.name, []))
        allowed_paths += target.folder["allowed_paths"].get(target.storage.name, [])

        files = scan_files(self.scannable, allowed_paths,
                           ignore_unreachable=self.config.ignore_unreachable)

        for s, n in files:
            self.cur_path = n["path"]

            worker.emit_event("next_node", s)

            if self.stopped:
                return False

            if n["type"] is not None:
                try:
                    self.flist.insert(n)
                except UnicodeError as e:
                    if not self.config.ignore_unreachable:
                        raise e

        self.status = "finished"

        return False

class EncryptedScanTask(ScanTask):
    def complete(self):
        if self.stopped:
            return False

        worker = get_current_worker()

        target = self.parent
        to_scan = [self.scannable]

        self.status = "pending"

        allowed_paths = list(self.config.allowed_paths.get(target.storage.name, []))
        allowed_paths += target.folder["allowed_paths"].get(target.storage.name, [])

        while not self.stopped:
            try:
                scannable = to_scan.pop(0)
            except IndexError:
                break

            self.cur_path = scannable.path

            scan_result = scannable.scan(allowed_paths,
                                         ignore_unreachable=self.config.ignore_unreachable)

            scannables = {}

            for s in scan_result["f"] + scan_result["d"]:
                if self.stopped:
                    return False

                worker.emit_event("next_node", s)
                path = pathm.dir_denormalize(s.path)
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

                try:
                    self.flist.insert(original.to_node())
                except UnicodeError as e:
                    if not self.config.ignore_unreachable:
                        raise e

                    continue

                if self.stopped:
                    return False

                if original.type == "d":
                    to_scan.append(original)

        if self.stopped:
            return False

        self.status = "finished"

        return True

class AsyncDecryptedScanTask(ScanTask):
    def complete(self):
        if self.stopped:
            return False

        worker = get_current_worker()

        target = self.parent
        scannable = self.scannable

        self.status = "pending"
        self.cur_path = scannable.path

        allowed_paths = list(self.config.allowed_paths.get(target.storage.name, []))
        allowed_paths += target.folder["allowed_paths"].get(target.storage.name, [])

        scan_result = scannable.scan(allowed_paths,
                                     ignore_unreachable=self.config.ignore_unreachable)

        for s in scan_result["f"] + scan_result["d"]:
            worker.emit_event("next_node", s)

            self.cur_path = s.path

            try:
                self.flist.insert(s.to_node())
            except UnicodeError as e:
                if not self.config.ignore_unreachable:
                    raise e

                continue

            if self.stopped:
                return False

            if s.type == "d":
                target.pool.add_task(AsyncDecryptedScanTask(target, s))

        del scan_result

        self.status = "finished"

        return True

class AsyncEncryptedScanTask(ScanTask):
    def complete(self):
        if self.stopped:
            return False

        worker = get_current_worker()

        target = self.parent
        scannable = self.scannable
        self.status = "pending"

        allowed_paths = list(self.config.allowed_paths.get(target.storage.name, []))
        allowed_paths += target.folder["allowed_paths"].get(target.storage.name, [])

        self.cur_path = scannable.path

        scan_result = scannable.scan(allowed_paths,
                                     ignore_unreachable=self.config.ignore_unreachable)

        scannables = {}

        for s in scan_result["f"] + scan_result["d"]:
            if self.stopped:
                return False

            worker.emit_event("next_node", s)

            path = pathm.dir_denormalize(s.path)
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

            try:
                self.flist.insert(original.to_node())
            except UnicodeError as e:
                if not self.config.ignore_unreachable:
                    raise e

                continue

            if self.stopped:
                return False

            if original.type == "d":
                target.pool.add_task(AsyncEncryptedScanTask(target, original))

        if self.stopped:
            return False

        self.status = "finished"

        return True
