#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from ...scan import do_scan
from ...Environment import Environment
from ....EncScript import Command

class LScanCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Scan local directories",
                                         prog=self.args[0])
        parser.add_argument("names", nargs="*")
        parser.add_argument("--ask", action="store_true")
        parser.add_argument("-a", "--all", action="store_true")
        parser.add_argument("--choose-targets", action="store_true")
        parser.add_argument("--no-journal", action="store_true")

        ns = parser.parse_args(self.args[1:])

        env = Environment(console.env)
        env["ask"] = ns.ask
        env["all"] = ns.all
        env["choose_targets"] = ns.choose_targets
        env["no_journal"] = ns.no_journal
        env["remote_only"] = False
        env["local_only"] = True

        return do_scan(env, ns.names)
