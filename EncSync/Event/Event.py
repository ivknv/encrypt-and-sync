#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

class Event(dict):
    def __init__(self, emitter, receiver, name, args, kwargs):
        dict.__init__(self, {"emitter": emitter,
                             "receiver": receiver,
                             "name": name,
                             "args": args,
                             "kwargs": kwargs})
        
        self._event = threading.Event()

    def wait(self):
        self._event.wait()

    def is_set(self):
        return self._event.is_set()

    @property
    def args(self):
        return self["args"]

    @property
    def kwargs(self):
        return self["kwargs"]

    @property
    def emitter(self):
        return self["emitter"]

    @property
    def reciever(self):
        return self["receiver"]

    @property
    def name(self):
        return self["name"]
