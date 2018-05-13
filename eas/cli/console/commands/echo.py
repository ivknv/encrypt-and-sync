#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ....encscript import Command

__all__ = ["EchoCommand"]

class EchoCommand(Command):
    def evaluate(self, console):
        print(" ".join(self.args[1:]))

        return 0
