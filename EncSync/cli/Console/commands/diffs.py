#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from ...show_diffs import show_diffs
from ...Environment import Environment
from ....EncScript import Command

__all__ = ["DiffsCommand"]

class DiffsCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Show differences",
                                         prog=self.args[0])
        parser.add_argument("target")

        ns = parser.parse_args(self.args[1:])
        env = Environment(console.env)

        return show_diffs(env, ns.target)
