# -*- coding: utf-8 -*-

import argparse

from ...sync import do_sync
from ...common import positive_int
from ...environment import Environment
from ....encscript import Command

__all__ = ["SyncCommand"]

class SyncCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Sync targets",
                                         prog=self.args[0])
        parser.add_argument("folders", nargs="*", help="List of folders/paths to sync")
        parser.add_argument("-a", "--all", action="store_true",
                            help="Sync all targets")
        parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                            help="Number of workers to use")
        parser.add_argument("--ask", action="store_true",
                            help="(deprecated)")
        parser.add_argument("--sync-ownership", action="store_true",
                            help="Sync ownership of files")
        parser.add_argument("--force-scan", action="store_true",
                            help="Always scan everything")
        parser.add_argument("--no-ask", action="store_true",
                            help="Don't ask for any user input")
        parser.add_argument("--choose-targets", action="store_true",
                            help="Choose which targets to sync")
        parser.add_argument("--no-sync-modified",
                            help="Don't try to sync modified date for files",
                            action="store_true")
        parser.add_argument("--no-sync-mode", action="store_true",
                            help="Don't try to sync file mode (permissions, owner, group, etc.)")
        parser.add_argument("--no-scan", action="store_true", help="Disable scan")
        parser.add_argument("--no-diffs", action="store_true",
                            help="Don't show the list of differences")
        parser.add_argument("--no-journal", action="store_true",
                            help="Disable SQLite3 journaling")
        parser.add_argument("--no-remove", action="store_true",
                            help="Don't remove any files (except for file duplicates)")
        parser.add_argument("--no-progress", action="store_true",
                            help="Don't show intermediate progress")
        parser.add_argument("-I", "--integrity-check", action="store_true",
                            help="Enable integrity check")

        ns = parser.parse_args(self.args[1:])

        env = Environment(console.env)
        env["all"] = ns.all
        env["ask"] = not ns.no_ask
        env["no_check"] = not ns.integrity_check
        env["no_scan"] = ns.no_scan
        env["no_diffs"] = ns.no_diffs
        env["choose_targets"] = ns.choose_targets
        env["no_journal"] = ns.no_journal
        env["no_remove"] = ns.no_remove
        env["no_progress"] = ns.no_progress
        env["no_sync_modified"] = ns.no_sync_modified
        env["no_sync_mode"] = ns.no_sync_mode
        env["sync_ownership"] = ns.sync_ownership
        env["force_scan"] = ns.force_scan

        if ns.n_workers is not None:
            env["n_workers"] = ns.n_workers

        return do_sync(env, ns.folders)
