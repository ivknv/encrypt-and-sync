#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import traceback
import weakref

from .event import Event

__all__ = ["Receiver"]

class Receiver(object):
    def receive(self, emitter, event_name, *args, **kwargs):
        event = Event(emitter, self, event_name, args, kwargs)

        self.handle_event(event)

        return event

    def handle_event(self, event):
        try:
            callback = getattr(self, "on_%s" % (event.name,))
        except AttributeError:
            return

        try:
            callback(event, *event.args, **event.kwargs)
        except:
            traceback.print_exc()