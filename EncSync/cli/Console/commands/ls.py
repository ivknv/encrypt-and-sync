#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys

from .... import Paths
from ....EncPath import EncPath

def cmd_ls(console, args):
    parser = argparse.ArgumentParser(description="List directory contents",
                                     prog=args[0])
    parser.add_argument("filenames", default=[console.cwd], nargs="*")

    return _cmd_ls(console, parser.parse_args(args[1:]))

def _cmd_ls(console, ns): 
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

        for response in console.encsync.ynd.ls(path):
            if response["success"]:
                if prefix is not None:
                    contents.append(encsync.decrypt_path(response["data"]["name"])[0])
                else:
                    contents.append(response["data"]["name"])
            else:
                print("Error: failed to get list of files", file=sys.stderr)
                return 1

        contents.sort()

        for i in contents:
            print(i)

    return 0
