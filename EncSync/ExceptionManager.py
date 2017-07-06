#!/usr/bin/env python
# -*- coding: utf-8 -*-

class ExceptionManager(object):
    def __init__(self):
        self._handlers = []

    def add(self, exc_type, func, *args, **kwargs):
        self._handlers.append((exc_type, func, args, kwargs))

    def get(self, exc_type):
        for i in self._handlers:
            if issubclass(exc_type, i[0]):
                return i

    def handle(self, exc):
        handler = self.get(type(exc))

        if handler is not None:
            return handler[1](exc, *handler[2], **handler[3])
