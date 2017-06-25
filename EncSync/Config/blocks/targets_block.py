#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from ... import Paths

def prepare_local_path(path):
    return os.path.realpath(os.path.expanduser(path))

def prepare_remote_path(path):
    return Paths.join_properly("/", path)

def exec_targets_block(config, args, commands):
    if len(args) != 0:
        raise ValueError("Invalid number of arguments: %d instead of 0" % len(args))

    for command in commands:
        if len(command) not in (2, 3):
            raise ValueError("Invalid number of arguments: %d instead of 2 or 3" % len(args))

        if len(command) == 2:
            local, remote = command
            name = None
        else:
            name, local, remote = command

        local  = prepare_local_path(local)
        remote = prepare_remote_path(remote)

        config.targets.append({"name":   name,
                               "local":  local,
                               "remote": remote})
