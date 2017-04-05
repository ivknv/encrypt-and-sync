#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from .Exceptions import UnknownEventError, DuplicateEventError

class Emitter(object):
    def __init__(self):
        self._events = set()
        self._events_lock = threading.Lock()

        self._receivers = []
        self._receivers_lock = threading.Lock()

    def add_event(self, event_name):
        with self._events_lock:
            if event_name in self._events:
                raise DuplicateEventError(event_name)

            self._events.add(event_name)

    def check_event(self, event_name):
        return event_name in self._events

    def add_receiver(self, receiver):
        with self._receivers_lock:
            self._receivers.append(receiver)

    def emit_event(self, event_name, *args, **kwargs):
        if not self.check_event(event_name):
            raise UnknownEventError(event_name)

        with self._receivers_lock:
            receivers = list(self._receivers)

        events = []

        for receiver in receivers:
            if receiver.is_active():
                events.append(receiver.receive(self, event_name, *args, **kwargs))

        return events
