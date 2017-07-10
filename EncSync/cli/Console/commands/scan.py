#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from .... import Paths
from ...scan import do_scan
from ...common import positive_int, recognize_path
from ...Environment import Environment
from ....EncScript import Command

class ScanCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Scan directories",
                                         prog=self.args[0])
        parser.add_argument("dirs", nargs="*")
        parser.add_argument("-a", "--all", action="store_true")
        parser.add_argument("--ask", action="store_true")
        parser.add_argument("--no-choice", action="store_true")
        parser.add_argument("--n-workers", "-w", type=positive_int)

        group = parser.add_mutually_exclusive_group()
        group.add_argument("--local-only", action="store_true")
        group.add_argument("--remote-only", action="store_true")

        ns = parser.parse_args(self.args[1:])

        paths = []

        for path in ns.dirs:
            path, path_type = recognize_path(path)

            if path_type == "remote":
                path = "disk://" + Paths.join_properly(console.cwd, path)

            paths.append(path)

        env = Environment(console.env)

        env["all"] = ns.all
        env["ask"] = ns.ask
        env["no_choice"] = ns.no_choice
        env["local_only"] = ns.local_only
        env["remote_only"] = ns.remote_only

        if ns.n_workers is not None:
            env["n_workers"] = ns.n_workers

        return do_scan(env, paths)
