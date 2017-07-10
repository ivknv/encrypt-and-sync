#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from ....EncScript import Command
from .... import Paths

class CdCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Change directory",
                                         prog=self.args[0])
        parser.add_argument("directory")

        ns = parser.parse_args(self.args[1:])

        if ns.directory == "-":
            console.cwd, console.pwd = console.pwd, console.cwd
            return 0

        console.pwd = console.cwd

        console.cwd = Paths.join_properly(console.cwd, ns.directory)

        return 0
