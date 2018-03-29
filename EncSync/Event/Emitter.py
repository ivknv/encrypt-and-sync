#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from .Exceptions import UnknownEventError, DuplicateEventError

__all__ = ["Emitter"]

class Emitter(object):
    def __init__(self):
        self._events = {}
        self._events_lock = threading.RLock()

        self._receivers = []
        self._receivers_lock = threading.RLock()

    def add_event(self, event_name):
        with self._events_lock:
            if event_name in self._events:
                raise DuplicateEventError(event_name)

            self._events[event_name] = threading.Event()

    def check_event(self, event_name):
        return event_name in self._events

    def get_event(self, event_name):
        try:
            return self._events[event_name]
        except KeyError:
            raise UnknownEventError(event_name)

    def wait_event(self, event_name):
        self.get_event(event_name).wait()

    def add_receiver(self, receiver):
        with self._receivers_lock:
            if receiver not in self._receivers:
                self._receivers.append(receiver)

    def remove_receiver(self, receiver):
        with self._receivers_lock:
            self._receivers.remove(receiver)

    def emit_event(self, event_name, *args, **kwargs):
        ev = self.get_event(event_name)

        ev.set()

        try:
            with self._receivers_lock:
                receivers = list(self._receivers)

            events = []

            for receiver in receivers:
                events.append(receiver.receive(self, event_name, *args, **kwargs))
        finally:
            ev.clear()

        return events
