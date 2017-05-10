#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys

from .... import paths

def cmd_ls(console, args):
    parser = argparse.ArgumentParser(description="List directory contents",
                                     prog=args[0])
    parser.add_argument("filenames", default=[console.cwd], nargs="*")

    _cmd_ls(console, parser.parse_args(args[1:]))

def _cmd_ls(console, ns): 
    filenames = ns.filenames

    for filename in filenames:
        path = paths.join_properly(console.cwd, filename)

        for response in console.encsync.ynd.ls(path):
            if response["success"]:
                print(response["data"]["name"])
            else:
                print("Error: failed to get list of files", file=sys.stderr)
                return
