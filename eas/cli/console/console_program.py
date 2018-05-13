#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ...encscript import Program
from .console_namespace import ConsoleNamespace

class ConsoleProgram(Program):
    def __init__(self, body):
        Program.__init__(self, body)
        self.namespace = ConsoleNamespace()

    def evaluate(self, console):
        return Program.evaluate(self, console)
