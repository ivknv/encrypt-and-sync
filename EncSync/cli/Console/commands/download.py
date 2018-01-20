#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from .... import Paths
from ...download import download
from ...common import positive_int, recognize_path
from ...Environment import Environment
from ....EncScript import Command

__all__ = ["DownloadCommand"]

class DownloadCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Download files/directories",
                                         prog=self.args[0])
        parser.add_argument("paths", nargs="+", help="List of paths to download")
        parser.add_argument("--n-workers", "-w", type=positive_int, metavar="N",
                            help="Number of workers to use")

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

        if ns.n_workers is not None:
            env["n_workers"] = ns.n_workers

        return download(env, paths)
