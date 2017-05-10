#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from io import BytesIO

from .... import paths

def cmd_cat(console, args):
    parser = argparse.ArgumentParser(description="Concatenate files to stdout",
                                     prog=args[0])
    parser.add_argument("filenames", nargs="+")

    _cmd_cat(console, parser.parse_args(args[1:]))

def _cmd_cat(console, ns): 
    for filename in ns.filenames:
        path = paths.join_properly(console.cwd, filename)

        buf = BytesIO()

        console.encsync.ynd.download(path, buf)

        for line in buf:
            print(line)
