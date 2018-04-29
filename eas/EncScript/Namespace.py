#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Namespace(dict):
    def __init__(self, parent=None, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)

        self.parent = parent

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError as e:
            if self.parent is None:
                raise e

            return self.parent[key]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default
