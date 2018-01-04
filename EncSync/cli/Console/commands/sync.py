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
        parser = argparse.ArgumentParser(description="Sync directories",
                                         prog=self.args[0])
        parser.add_argument("targets", nargs="*")
        parser.add_argument("-a", "--all", action="store_true")
        parser.add_argument("--n-workers", "-w", type=positive_int)
        parser.add_argument("--ask", action="store_true")
        parser.add_argument("--choose-targets", action="store_true")
        parser.add_argument("--no-scan", action="store_true")
        parser.add_argument("--no-diffs", action="store_true")
        parser.add_argument("--no-journal", action="store_true")
        parser.add_argument("-I", "--integrity-check", action="store_true")

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

        return do_sync(env, ns.targets)
