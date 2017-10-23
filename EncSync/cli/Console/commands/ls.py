#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys

import yadisk.exceptions

from .... import Paths
from ....EncPath import EncPath
from ....EncScript import Command

class LsCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="List directory contents",
                                         prog=self.args[0])
        parser.add_argument("filenames", default=[console.cwd], nargs="*")

        ns = parser.parse_args(self.args[1:])

        filenames = ns.filenames
        encsync = console.encsync

        for filename in filenames:
            path = Paths.join_properly(console.cwd, filename)
            prefix = encsync.find_encrypted_dir(path)

            if prefix is not None:
                encpath = EncPath(encsync)
                encpath.remote_prefix = prefix
                encpath.path = Paths.cut_prefix(path, prefix)
                IVs = encpath.get_IVs_from_db(console.env["config_dir"])
                encpath.IVs = IVs

                if encpath.remote_prefix != encpath.remote and not IVs:
                    print("Error: requested path doesn't exist", file=sys.stderr)
                    return 1

                path = encpath.remote_enc

            contents = []

            for response in console.encsync.ynd.listdir(path):
                try:
                    if prefix is not None:
                        contents.append(encsync.decrypt_path(response.name)[0])
                    else:
                        contents.append(response.name)
                except yadisk.exceptions.YaDiskError as e:
                    print("Error: %s" % (e,), file=sys.stderr)
                    return 1

            contents.sort()

            for i in contents:
                print(i)

        return 0
