#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ... import Paths

def prepare_remote_path(path):
    return Paths.join_properly("/", path)

def exec_encrypted_dirs_block(config, args, commands):
    if len(args) != 0:
        raise ValueError("Invalid number of arguments: %d instead of 0" % len(args))

    config.encrypted_dirs.clear()

    for command in commands:
        if len(command) != 1:
            raise ValueError("Expected only one path")

        path = prepare_remote_path(command[0])

        config.encrypted_dirs.add(path)
