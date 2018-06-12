#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from .... import pathm
from ....encscript import Command
from ...common import show_error, recognize_path

__all__ = ["LsCommand"]

class LsCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="List directory contents",
                                         prog=self.args[0])
        parser.add_argument("paths", default=[console.cwd], nargs="*",
                            help="pathm to list contents for")

        ns = parser.parse_args(self.args[1:])

        paths = ns.paths

        for path in paths:
            path, path_type = recognize_path(path, console.cur_storage.name)

            if path_type == console.cur_storage.name:
                path = pathm.join_properly(console.cwd, path)
                storage = console.cur_storage
            else:
                path = pathm.join_properly("/", path)
                storage = console.get_storage(path_type)

            try:
                contents = [i["name"]
                            for i in sorted(storage.listdir(path),
                                            key=lambda x: x["name"])]
            except NotADirectoryError:
                contents = [pathm.dir_denormalize(pathm.split(path)[1])]
            except IOError as e:
                show_error("I/O error: %s" % (e,))
                return 1

            for name in contents:
                print(name)

        return 0
