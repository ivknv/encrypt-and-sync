# -*- coding: utf-8 -*-

import threading

from .events import Emitter

__all__ = ["TargetRunner"]

class TargetRunner(Emitter):
    """
        Events: next_target, error
    """

    def __init__(self, config, directory, enable_journal=True):
        Emitter.__init__(self)

        self.stopped = False
        self.cur_target = None

        self.config = config
        self.directory = directory
        self.enable_journal = enable_journal

        self._targets = []
        self._target_lock = threading.Lock()

        self._upload_limit = float("inf")
        self._download_limit = float("inf")

    @property
    def upload_limit(self):
        return self._upload_limit

    @upload_limit.setter
    def upload_limit(self, value):
        self._upload_limit = value

        for target in self.get_target_list() + [self.cur_target]:
            if target is None:
                continue

            target.upload_limit = value

    @property
    def download_limit(self):
        return self._download_limit

    @download_limit.setter
    def download_limit(self, value):
        self._download_limit = value

        for target in self.get_target_list() + [self.cur_target]:
            if target is None:
                continue

            target.download_limit = value

    def get_target_list(self):
        with self._target_lock:
            return list(self._targets)

    def add_target(self, target):
        with self._target_lock:
            self._targets.append(target)

        return target

    def stop(self):
        self.stopped = True

        # Intentional assignment for thread safety
        target = self.cur_target

        if target is not None:
            target.stop()

    def change_status(self, status):
        for target in self.get_target_list() + [self.cur_target]:
            if target is not None:
                target.status = status

    def run(self):
        try:
            while not self.stopped:
                with self._target_lock:
                    try:
                        target = self._targets.pop(0)
                    except IndexError:
                        break

                    self.cur_target = target

                try:
                    self.emit_event("next_target", target)

                    if target.status == "suspended":
                        self.cur_target = None
                        continue

                    target.status = "pending"
                    target.run()

                    self.cur_target = None
                except Exception as e:
                    self.emit_event("error", e)
                    target.status = "failed"
        finally:
            self.cur_target = None
