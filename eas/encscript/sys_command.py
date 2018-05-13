#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shlex
import subprocess

from .command import Command

class SysCommand(Command):
    def __init__(self, command):
        Command.__init__(self, shlex.split(command))

    def evaluate(self, *args, **kwargs):
        try:
            return subprocess.call(self.args)
        except FileNotFoundError as e:
            print("Error: no such file or directory: %r" % e.filename)
            return 127
        except subprocess.SubprocessError as e:
            print("Error: %s" % e)
            return 1
