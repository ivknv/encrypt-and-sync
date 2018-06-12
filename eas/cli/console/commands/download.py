#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from .... import pathm
from ...download import download
from ...common import positive_int, recognize_path
from ...environment import Environment
from ....encscript import Command

__all__ = ["DownloadCommand"]

class DownloadCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Download files/directories",
                                         prog=self.args[0])
        parser.add_argument("paths", nargs="+", help="List of paths to download")
        parser.add_argument("--no-progress", action="store_true",
                            help="Don't show intermediate progress")
        parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                            help="Number of workers to use")
        parser.add_argument("--no-ask", action="store_true",
                            help="Don't ask for any user input")
        parser.add_argument("--no-skip", action="store_true",
                            help="Don't skip already downloaded files")

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

        env["no_progress"] = ns.no_progress
        env["ask"] = not ns.no_ask
        env["no_skip"] = ns.no_skip

        if ns.n_workers is not None:
            env["n_workers"] = ns.n_workers

        return download(env, paths)
