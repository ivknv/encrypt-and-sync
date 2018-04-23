# -*- coding: utf-8 -*-

import functools

__all__ = ["LazyDict"]

class LazyDict(dict):
    def __init__(self, x=None, **kwargs):
        dict.__init__(self)

        self.update(x, **kwargs)
        
    def get(self, key, default=None):
        return dict.get(self, key, lambda: default)()

    def setdefault(self, key, value):
        return dict.setdefault(self, key, functools.lru_cache()(value))

    def __getitem__(self, key):
        return dict.__getitem__(self, key)()

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, functools.lru_cache()(value))

    def values(self):
        for value in dict.values(self):
            yield value()

    def items(self):
        for k, v in dict.items(self):
            yield k, v()

    def update(self, d=None, **kwargs):
        if not d:
            d = kwargs

        if isinstance(d, LazyDict):
            for k, v in dict.items(d):
                dict.__setitem__(self, k, v)
        elif isinstance(d, dict):
            for k, v in dict.items(d):
                self[k] = v
        else:
            for k, v in d:
                self[k] = v

    def fromkeys(self, keys, value=None):
        return LazyDict({k: value for k in keys})

    def copy(self):
        return LazyDict(self)
