#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["Event"]

class Event(dict):
    def __init__(self, emitter, receiver, name, args, kwargs):
        dict.__init__(self, {"emitter": emitter,
                             "receiver": receiver,
                             "name": name,
                             "args": args,
                             "kwargs": kwargs})

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
