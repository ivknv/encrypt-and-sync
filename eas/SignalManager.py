#!/usr/bin/env python
# -*- coding: utf-8 -*-

import signal

class SignalManager(object):
    def __init__(self):
        self.handlers = {}
        self.saved_handlers = {}

    def __enter__(self):
        for signum, handler in self.handlers.items():
            if handler is None:
                continue

            self.save(signum, signal.signal(signum, handler))

    def __exit__(self, type, value, traceback):
        for signum in self.saved_handlers.keys():
            signal.signal(signum, self.get_saved(signum))

        self.saved_handlers.clear()

    def set(self, signum, handler):
        self.handlers[signum] = handler

    def save(self, signum, handler):
        self.saved_handlers[signum] = handler

    def get_saved(self, signum):
        return self.saved_handlers.get(signum, signal.SIG_DFL)

    def get(self, signum):
        return self.handlers.get(signum, None)
