# -*- coding: utf-8 -*-

import argparse

from .... import Paths
from ....EncScript import Command
from ...common import positive_int, recognize_path
from ...remove_duplicates import remove_duplicates
from ...Environment import Environment

__all__ = ["RemoveDuplicatesCommand"]

class RemoveDuplicatesCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Remove duplicates",
                                         prog=self.args[0])
        parser.add_argument("paths", nargs="*")
        parser.add_argument("-a", "--all", action="store_true")
        parser.add_argument("--ask", action="store_true")
        parser.add_argument("--choose-targets", action="store_true")
        parser.add_argument("--no-journal", action="store_true")
        parser.add_argument("--src-only", action="store_true")
        parser.add_argument("--dst-only", action="store_true")
        parser.add_argument("--n-workers", "-w", type=positive_int)

        ns = parser.parse_args(self.args[1:])
        paths = []

        for path in ns.paths:
            path, path_type = recognize_path(path, console.cur_storage.name)

            if path_type == console.cur_storage.name:
                path = path_type + "://" + Paths.join_properly(console.cwd, path)
            else:
                path = path_type + "://" + path

            paths.append(path)

        env = Environment(console.env)

        env["all"] = ns.all
        env["ask"] = ns.ask
        env["src_only"] = ns.src_only
        env["dst_only"] = ns.dst_only
        env["choose_targets"] = ns.choose_targets
        env["no_journal"] = ns.no_journal

        if ns.n_workers is not None:
            env["n_workers"] = ns.n_workers

        return remove_duplicates(env, paths)
