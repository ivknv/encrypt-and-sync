#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ...common import show_error

def cmd_exit(console, args):
    if len(args) >= 2:
        try:
            ret = int(args[1]) % 256
            if ret < 0:
                raise ValueError
        except ValueError:
            ret = 128
            show_error("Error: invalid exit code: %r" % args[1])
    else:
        ret = 0

    console.quit = True

    return ret
