#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ...EncScript import Program
from .ConsoleNamespace import ConsoleNamespace

class ConsoleProgram(Program):
    def __init__(self, body):
        Program.__init__(self, body)
        self.namespace = ConsoleNamespace()

    def evaluate(self, console):
        return Program.evaluate(self, console)
