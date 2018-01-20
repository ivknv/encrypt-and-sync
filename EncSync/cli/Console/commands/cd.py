#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os

from ....EncScript import Command
from .... import Paths

from ...common import show_error, recognize_path

__all__ = ["CdCommand"]

class CdCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Change directory",
                                         prog=self.args[0])
        parser.add_argument("directory")

        ns = parser.parse_args(self.args[1:])

        if ns.directory == "-":
            console.cwd, console.pwd = console.pwd, console.cwd
            cur_storage, previous_storage = console.cur_storage, console.previous_storage
            console.cur_storage, console.previous_storage = previous_storage, cur_storage
            return 0

        path, path_type = recognize_path(ns.directory, console.cur_storage.name)

        if path_type == console.cur_storage.name:
            new_path = Paths.join_properly(console.cwd, path)
            storage = console.cur_storage
        else:
            new_path = Paths.join_properly("/", path)            
            storage = console.get_storage(path_type)

        try:
            meta = storage.get_meta(new_path)
        except FileNotFoundError:
            show_error("Path doesn't exist: %r" % (new_path,))
            return 1

        if meta["type"] != "dir":
            show_error("%r is not a directory" % (new_path,))
            return 1

        if path_type != console.cur_storage.name:
            console.change_storage(path_type, new_path)
        else:
            console.cwd, console.pwd = new_path, console.cwd

        if path_type == "local":
            os.chdir(Paths.to_sys(console.cwd))

        return 0
