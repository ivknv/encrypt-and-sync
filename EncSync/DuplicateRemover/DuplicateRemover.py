# -*- coding: utf-8 -*-

import threading

from .. import Paths
from ..Worker import Worker
from ..LogReceiver import LogReceiver
from .Logging import logger
from .Target import DuplicateRemoverTarget

__all__ = ["DuplicateRemover"]

class DuplicateRemover(Worker):
    def __init__(self, config, directory, n_workers=2, enable_journal=True):
        Worker.__init__(self)

        self.config = config
        self.directory = directory
        self.n_workers = n_workers
        self.enable_journal = enable_journal

        self.targets = []
        self.targets_lock = threading.Lock()
        self.cur_target = None

        self.add_event("next_target")
        self.add_event("error")

        self.add_receiver(LogReceiver(logger))

    def get_targets(self):
        with self.targets_lock:
            return list(self.targets)

    def change_status(self, status):
        for target in self.get_targets() + [self.cur_target]:
            if target is not None:
                target.status = status

    def make_target(self, storage_name, path):
        path = Paths.join_properly("/", path)
        target = DuplicateRemoverTarget(self)
        target.path = path
        target.storage = self.config.storages[storage_name]

        config_target, dir_type = self.config.identify_target(storage_name, path)

        if config_target is None:
            msg = "%r does not belong to any targets" % (storage_name + "://" + path,)
            raise ValueError(msg)

        if not config_target[dir_type]["encrypted"]:
            raise ValueError("%r is not encrypted" % (storage_name + "://" + path,))

        encoding = config_target[dir_type]["filename_encoding"]
        target.filename_encoding = encoding
        target.prefix = config_target[dir_type]["path"]

        return target

    def add_target(self, target):
        with self.targets_lock:
            self.targets.append(target)

            return target

    def add_new_target(self, storage_name, path):
        return self.add_target(self.make_target(storage_name, path))

    def stop(self):
        Worker.stop(self)

        # Intentional assignment for thread safety
        target = self.cur_target

        if target is not None:
            target.stop()

    def work(self):
        while not self.stopped:
            with self.targets_lock:
                try:
                    target = self.targets.pop(0)
                    self.cur_target = target
                except IndexError:
                    break

            try:
                if self.stopped:
                    break

                self.emit_event("next_target", target)

                target.complete(self)
            except Exception as e:
                self.emit_event("error", e)
                self.cur_target.status = "failed"
            finally:
                self.cur_target = None
