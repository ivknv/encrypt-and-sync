#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from ...scan import do_scan
from ...common import positive_int

def cmd_lscan(console, args):
    parser = argparse.ArgumentParser(description="Scan local directories",
                                     prog=args[0])
    parser.add_argument("dirs", nargs="+")
    parser.add_argument("--n-workers", default=1, type=positive_int)

    ns = parser.parse_args(args[1:])

    return do_scan(["local://" + i for i in ns.dirs], ns.n_workers)
