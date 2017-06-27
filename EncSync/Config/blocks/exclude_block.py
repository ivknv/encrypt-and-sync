#!/usr/bin/env python
# -*- coding: utf-8 -*-

def exec_exclude_block(config, args, commands):
    if args:
        raise ValueError("Invalud number of arguments: %d instead of 0" % len(args))

    patterns = []

    for command in commands:
        if len(command) != 1:
            raise ValueError("Expected only 1 pattern, got %d instead" % len(command))

        pattern = command[0]
        patterns.append(pattern)

    config.allowed_paths.append(["e", patterns])
