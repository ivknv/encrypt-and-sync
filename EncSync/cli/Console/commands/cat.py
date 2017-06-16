#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from io import BytesIO
import sys

from .... import Paths
from ....EncPath import EncPath

def cmd_cat(console, args):
    parser = argparse.ArgumentParser(description="Concatenate files to stdout",
                                     prog=args[0])
    parser.add_argument("filenames", nargs="+")

    return _cmd_cat(console, parser.parse_args(args[1:]))

def _cmd_cat(console, ns):
    encsync = console.encsync

    for filename in ns.filenames:
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

        if not encsync.ynd.is_file(path):
            print("Error: requested path is not a file or doesn't exist", file=sys.stderr)
            return 1

        enc_buf = BytesIO()
        dec_buf = BytesIO()

        console.encsync.ynd.download(path, enc_buf)
        enc_buf.seek(0)
        encsync.decrypt_file(enc_buf, dec_buf)
        dec_buf.seek(0)
        enc_buf.truncate(0)

        for line in dec_buf:
            print(line.decode("utf8"), end="")

    return 0
