#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from ...sync import do_sync
from ...common import positive_int
from ...Environment import Environment
from ....EncScript import Command

__all__ = ["SyncCommand"]

class SyncCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Sync targets",
                                         prog=self.args[0])
        parser.add_argument("folders", nargs="*", help="List of folders to sync")
        parser.add_argument("-a", "--all", action="store_true",
                            help="Sync all targets")
        parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                            help="Number of workers to use")
        parser.add_argument("--ask", action="store_true",
                            help="Ask for user's action in certain cases")
        parser.add_argument("--choose-targets", action="store_true",
                            help="Choose which targets to sync")
        parser.add_argument("--no-scan", action="store_true", help="Disable scan")
        parser.add_argument("--no-diffs", action="store_true",
                            help="Don't show the list of differences")
        parser.add_argument("--no-journal", action="store_true",
                            help="Disable SQLite3 journaling")
        parser.add_argument("-I", "--integrity-check", action="store_true",
                            help="Enable integrity check")

        ns = parser.parse_args(self.args[1:])

        env = Environment(console.env)
        env["all"] = ns.all
        env["ask"] = ns.ask
        env["no_check"] = not ns.integrity_check
        env["no_scan"] = ns.no_scan
        env["no_diffs"] = ns.no_diffs
        env["choose_targets"] = ns.choose_targets
        env["no_journal"] = ns.no_journal

        if ns.n_workers is not None:
            env["n_workers"] = ns.n_workers

        return do_sync(env, ns.folders)
