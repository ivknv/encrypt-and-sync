#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Exceptions import UnknownStageError, DuplicateStageError

from .Worker import Worker

class StagedWorker(Worker):
    def __init__(self, parent=None, daemon=False):
        Worker.__init__(self, parent, daemon)

        self.stage = None
        self.available = True

        self.stages = {}

        self.add_event("entered_stage")
        self.add_event("exited_stage")

    def run_stage(self, stage):
        try:
            self.enter_stage(stage)
            self.join_workers()
        finally:
            if self.stage is not None:
                self.exit_stage()

    def add_stage(self, name, on_enter=None, on_exit=None):
        stage = {"name":  name,
                 "enter": on_enter,
                 "exit":  on_exit}

        if name in self.stages:
            raise DuplicateStageError(name)

        self.stages[name] = stage

    def enter_stage(self, name):
        assert(self.stage is None)
        assert(name is not None)

        try:
            self.stage = self.stages[name]
        except KeyError:
            raise UnknownStageError(name)

        self.available = True

        self.emit_event("entered_stage", name)

        enter_callback = self.stage["enter"]

        if enter_callback:
            enter_callback()

    def exit_stage(self):
        assert(self.stage is not None)

        self.available = False

        self.stop_workers()

        exit_callback = self.stage["exit"]

        try:
            if exit_callback:
                exit_callback()
        finally:
            self.emit_event("exited_stage", self.stage["name"])
            self.stage = None