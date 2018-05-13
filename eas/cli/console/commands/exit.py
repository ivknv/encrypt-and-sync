#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ....encscript import Command
from ...common import show_error

__all__ = ["ExitCommand"]

class ExitCommand(Command):
    def evaluate(self, console):
        if len(self.args) >= 2:
            try:
                ret = int(self.args[1]) % 256
                if ret < 0:
                    raise ValueError
            except ValueError:
                ret = 128
                show_error("Error: invalid exit code: %r" % self.args[1])
        else:
            ret = 0

        console.quit = True

        return ret
