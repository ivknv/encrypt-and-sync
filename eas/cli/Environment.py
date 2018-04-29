#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["Environment"]

class Environment(dict):
    def __init__(self, parent=None):
        dict.__init__(self)

        self.parent = parent

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError as e:
            if self.parent is not None:
                return self.parent[key]
            raise e

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            if self.parent is not None:
                return self.parent.get(key, default)

            return default
