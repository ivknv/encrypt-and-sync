#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Element(object):
    def __init__(self, root=None):
        self.x, self.y = 0, 0

        self.root = root
        self.key_handlers = []

    def handle_key(self, k):
        for handler, args, kwargs, keys in self.key_handlers:
            if k in keys or len(keys) == 0:
                handler(k, *args, **kwargs)

    @property
    def focused(self):
        return self is self.root.focused_element

    def focus(self):
        self.root.focused_element = self

    def unfocus(self):
        if self.focused:
            self.root.focused_element = None

    def add_key_handler(self, keys, func, *args, **kwargs):
        self.key_handlers.append([func, args, kwargs, keys])

    def display(self, window, ox=0, oy=0):
        raise NotImplementedError
