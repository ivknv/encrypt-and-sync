#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys

from ....encscript import Command

from .... import pathm
from ...common import recognize_path

__all__ = ["CatCommand"]

class CatCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Concatenate files to stdout",
                                         prog=self.args[0])
        parser.add_argument("paths", nargs="+", help="List of files to concatenate")

        ns = parser.parse_args(self.args[1:])

        for path in ns.paths:
            path, path_type = recognize_path(path, console.cur_storage.name)

            if path_type == console.cur_storage.name:
                path = pathm.join_properly(console.cwd, path)
                storage = console.cur_storage
            else:
                path = pathm.join_properly("/", path)
                storage = console.get_storage(path_type)

            generator = storage.get_file(path)
            task = next(generator)
            f = next(generator)

            for line in f:
                sys.stdout.buffer.write(line)

        return 0
