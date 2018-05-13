#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from ...show_diffs import show_diffs
from ...environment import Environment
from ....encscript import Command

__all__ = ["DiffsCommand"]

class DiffsCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Show differences between directories",
                                         prog=self.args[0])
        parser.add_argument("folders", nargs=2, help="Folders to show differences for")

        ns = parser.parse_args(self.args[1:])
        env = Environment(console.env)

        return show_diffs(env, *ns.folders[:2])
