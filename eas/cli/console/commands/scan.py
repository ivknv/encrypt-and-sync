# -*- coding: utf-8 -*-

import argparse

from ...scan import do_scan
from ...common import positive_int
from ...environment import Environment
from ....encscript import Command

__all__ = ["ScanCommand"]

class ScanCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Scan folders/paths",
                                         prog=self.args[0])
        parser.add_argument("folders", nargs="*", help="List of folders/paths to scan")
        parser.add_argument("-a", "--all", action="store_true",
                            help="Scan all folders")
        parser.add_argument("--ask", action="store_true",
                            help="(deprecated)")
        parser.add_argument("--no-ask", action="store_true",
                            help="Don't ask for any user input")
        parser.add_argument("--choose-targets", action="store_true",
                            help="Choose which folders to scan")
        parser.add_argument("--no-journal", action="store_true",
                            help="Disable SQLite3 journaling")
        parser.add_argument("--no-progress", action="store_true",
                            help="Don't show intermediate progress")
        parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                            help="Number of workers to use")

        ns = parser.parse_args(self.args[1:])

        env = Environment(console.env)

        env["all"] = ns.all
        env["ask"] = not ns.no_ask
        env["choose_targets"] = ns.choose_targets
        env["no_journal"] = ns.no_journal
        env["no_progress"] = ns.no_progress

        if ns.n_workers is not None:
            env["n_workers"] = ns.n_workers

        return do_scan(env, ns.folders)
