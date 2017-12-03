#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from io import BytesIO
import sys

from ....EncScript import Command

from .... import Paths
from ....EncPath import EncPath

class CatCommand(Command):
    def evaluate(self, console):
        parser = argparse.ArgumentParser(description="Concatenate files to stdout",
                                         prog=self.args[0])
        parser.add_argument("filenames", nargs="+")

        ns = parser.parse_args(self.args[1:])

        encsync = console.encsync

        for filename in ns.filenames:
            path = Paths.join_properly(console.cwd, filename)
            target = encsync.find_target_by_remote_path(path)
            filename_encoding = target["filename_encoding"]
            prefix = target["remote"]

            if prefix is not None:
                encpath = EncPath(encsync, None, filename_encoding)
                encpath.remote_prefix = prefix
                encpath.path = Paths.cut_prefix(path, prefix)

                IVs = encpath.get_IVs_from_db(None, console.env["db_dir"])
                encpath.IVs = IVs

                if encpath.remote_prefix != encpath.remote and not IVs:
                    print("Error: requested path doesn't exist", file=sys.stderr)
                    return 1

                path = encpath.remote_enc

            if not encsync.ynd.is_file(path):
                print("Error: requested path is not a file or doesn't exist", file=sys.stderr)
                return 1

            enc_buf = BytesIO()
            dec_buf = BytesIO()

            console.encsync.ynd.download(path, enc_buf)
            enc_buf.seek(0)

            encsync.decrypt_file(enc_buf, dec_buf)
            del enc_buf
            dec_buf.seek(0)

            for line in dec_buf:
                print(line.decode("utf8"), end="")

        return 0
