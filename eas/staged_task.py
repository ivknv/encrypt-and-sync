# -*- coding: utf-8 -*-

from .task import Task

__all__ = ["StagedTask"]

class StagedTask(Task):
    """
        Events: entered_stage, exited_stage
    """

    def __init__(self):
        Task.__init__(self)

        self._stages = {}
        self._stage = None

    @property
    def stage(self):
        return self._stage

    def run_stage(self, name):
        try:
            self.enter_stage(name)
        finally:
            if self._stage is not None:
                self.exit_stage()

    def set_stage(self, name, on_enter=None, on_exit=None):
        stage = {"name":  name,
                 "enter": on_enter,
                 "exit":  on_exit}

        self._stages[name] = stage

    def get_stage(self, name):
        try:
            return self._stages[name]
        except KeyError:
            raise KeyError("Unknown stage: %r" % (name,))

    def enter_stage(self, name):
        assert(self._stage is None)
        assert(name is not None)

        try:
            self._stage = self._stages[name]
        except KeyError:
            raise KeyError("Unknown stage: %r" % (name,))

        self.emit_event("entered_stage", name)

        enter_callback = self._stage["enter"]

        if enter_callback:
            enter_callback()

    def exit_stage(self):
        assert(self._stage is not None)

        exit_callback = self._stage["exit"]

        try:
            if exit_callback:
                exit_callback()
        finally:
            self.emit_event("exited_stage", self._stage["name"])
            self._stage = None
