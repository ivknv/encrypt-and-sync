#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from .... import Paths
from ...show_diffs import show_diffs
from ...Environment import Environment
from ...common import recognize_path, local_path, non_local_path
from ....EncScript import Command

class DiffsCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Show differences",
                                         prog=self.args[0])
        parser.add_argument("local", type=local_path)
        parser.add_argument("remote", type=non_local_path)

        ns = parser.parse_args(self.args[1:])

        ns.local = recognize_path(ns.local)[0]
        ns.remote = Paths.join_properly(console.cwd, recognize_path(ns.remote)[0])

        env = Environment(console.env)

        return show_diffs(env, ns.local, ns.remote)
