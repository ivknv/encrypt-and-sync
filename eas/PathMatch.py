#!/usr/bin/env python
# -*- coding: utf-8 -*-

import fnmatch
import re

__all__ = ["compile_patterns", "match"]

def compile_patterns(patterns):
    return [[lst_type, [re.compile(fnmatch.translate(i)) for i in lst]]
            for lst_type, lst in patterns]

def match(path, patterns):
    include = True

    for lst_type, lst in patterns:
        if lst_type == "i":
            if include:
                continue

            for pattern in lst:
                if pattern.match(path):
                    include = True
                    break
        elif lst_type == "e":
            if not include:
                continue

            for pattern in lst:
                if pattern.match(path):
                    include = False
                    break
    return include
