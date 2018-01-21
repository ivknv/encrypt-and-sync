#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from ...scan import do_scan
from ...common import positive_int
from ...Environment import Environment
from ....EncScript import Command

__all__ = ["ScanCommand"]

class ScanCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Scan targets",
                                         prog=self.args[0])
        parser.add_argument("targets", nargs="*", help="List of targets to scan")
        parser.add_argument("-a", "--all", action="store_true",
                            help="Scan all targets")
        parser.add_argument("--ask", action="store_true",
                            help="Ask for user's action in certain cases")
        parser.add_argument("--choose-targets", action="store_true",
                            help="Choose which targets to scan")
        parser.add_argument("--no-journal", action="store_true",
                            help="Disable SQLite3 journaling")
        parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                            help="Number of workers to use")

        group = parser.add_mutually_exclusive_group()
        group.add_argument("--src-only", action="store_true",
                           help="Scan only source paths")
        group.add_argument("--dst-only", action="store_true",
                           help="Scan only destination paths")

        ns = parser.parse_args(self.args[1:])

        env = Environment(console.env)

        env["all"] = ns.all
        env["ask"] = ns.ask
        env["choose_targets"] = ns.choose_targets
        env["no_journal"] = ns.no_journal
        env["src_only"] = ns.src_only
        env["dst_only"] = ns.dst_only

        if ns.n_workers is not None:
            env["n_workers"] = ns.n_workers

        return do_scan(env, ns.targets)
