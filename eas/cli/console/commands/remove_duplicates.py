# -*- coding: utf-8 -*-

import argparse

from .... import pathm
from ....encscript import Command
from ...common import positive_int, recognize_path
from ...remove_duplicates import remove_duplicates
from ...environment import Environment

__all__ = ["RemoveDuplicatesCommand"]

class RemoveDuplicatesCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Remove duplicates",
                                         prog=self.args[0])
        parser.add_argument("paths", nargs="*", help="pathm to remove duplicates from")
        parser.add_argument("-a", "--all", action="store_true",
                            help="Remove duplicates from all folders")
        parser.add_argument("--ask", action="store_true", help="(deprecated)")
        parser.add_argument("--no-ask", action="store_true",
                            help="Don't ask for any user input")
        parser.add_argument("--choose-targets", action="store_true",
                            help="Choose which folders to remove duplicates for")
        parser.add_argument("--no-preserve-modified", action="store_true",
                            help="Don't try to preserve modified date of directories")
        parser.add_argument("--no-journal", action="store_true",
                            help="Disable SQLite3 journaling")
        parser.add_argument("--no-progress", action="store_true",
                            help="Don't show intermediate progress")
        parser.add_argument("--n-workers", "-w", type=positive_int,
                            help="Number of workers to use")

        ns = parser.parse_args(self.args[1:])
        paths = []

        for path in ns.paths:
            path, path_type = recognize_path(path, console.cur_storage.name)

            if path_type == console.cur_storage.name:
                path = path_type + "://" + pathm.join_properly(console.cwd, path)
            else:
                path = path_type + "://" + path

            paths.append(path)

        env = Environment(console.env)

        env["all"] = ns.all
        env["ask"] = not ns.no_ask
        env["choose_targets"] = ns.choose_targets
        env["no_journal"] = ns.no_journal
        env["no_progress"] = ns.no_progress
        env["no_preserve_modified"] = ns.no_preserve_modified

        if ns.n_workers is not None:
            env["n_workers"] = ns.n_workers

        return remove_duplicates(env, paths)
