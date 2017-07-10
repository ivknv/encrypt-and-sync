#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from .... import Paths
from ...scan import do_scan
from ...common import positive_int
from ...Environment import Environment
from ....EncScript import Command

class RScanCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Scan remote directories",
                                         prog=self.args[0])
        parser.add_argument("dirs", nargs="*")
        parser.add_argument("--ask", action="store_true")
        parser.add_argument("-a", "--all", action="store_true")
        parser.add_argument("--no-choice", action="store_true")
        parser.add_argument("--n-workers", "-w", type=positive_int)

        ns = parser.parse_args(self.args[1:])

        paths = ["disk://" + Paths.join_properly(console.cwd, i) for i in ns.dirs]

        env = Environment(console.env)

        env["ask"] = ns.ask
        env["all"] = ns.all
        env["no_choice"] = ns.no_choice
        env["local_only"] = False
        env["remote_only"] = True

        if ns.n_workers is not None:
            env["n_workers"] = ns.n_workers

        return do_scan(env, paths)
