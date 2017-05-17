#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from .... import Paths

def cmd_cd(console, args):
    parser = argparse.ArgumentParser(description="Change directory", prog=args[0])
    parser.add_argument("directory")

    _cmd_cd(console, parser.parse_args(args[1:]))

def _cmd_cd(console, ns): 
    if ns.directory == "-":
        console.cwd, console.pwd = console.pwd, console.cwd
        return

    console.pwd = console.cwd

    console.cwd = Paths.join_properly(console.cwd, ns.directory)
