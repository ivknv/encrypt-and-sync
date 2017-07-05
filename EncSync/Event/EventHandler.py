#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import traceback
import weakref

from .Exceptions import UnknownEventError, DuplicateEventError
from .Event import Event

class EventHandler(object):
    def __init__(self):
        self._events = {}
        self._events_lock = threading.RLock()

        self._receivers = []
        self._receivers_lock = threading.RLock()

        self._callbacks = {}
        self._callbacks_lock = threading.RLock()

        self.add_event("event")

    def add_callback(self, event_name, callback):
        with self._callbacks_lock:
            self._callbacks.setdefault(event_name, [])
            self._callbacks[event_name].append(callback)

        return callback

    def add_emitter_callback(self, emitter, event_name, callback):
        def new_callback(event, *args, **kwargs):
            if weak_emitter.alive and event["emitter"] is weak_emitter.peek()[0]:
                return callback(event, *args, **kwargs)

        weak_emitter = weakref.finalize(emitter,    self.remove_callback,
                                        event_name, new_callback)

        return self.add_callback(event_name, new_callback)

    def remove_callback(self, event_name, callback):
        with self._callbacks_lock:
            try:
                self._callbacks[event_name].remove(callback)
                return True
            except (IndexError, ValueError):
                return False

    def add_propagation(self, emitter, *events):
        def callback(event, *args, **kwargs):
            receiver = event["receiver"]
            receiver.emit_event(event["name"], *args, **kwargs)

        for event_name in events:
            try:
                self.add_event(event_name)
            except DuplicateEventError:
                pass
            self.add_emitter_callback(emitter, event_name, callback)

    def receive(self, emitter, event_name, *args, **kwargs):
        event = Event(emitter, self, event_name, args, kwargs)

        self.handle_event(event)

        return event

    def get_callbacks(self, event_name):
        with self._callbacks_lock:
            return list(self._callbacks.get(event_name, []))

    def handle_event(self, event):
        callbacks = self.get_callbacks(event["name"])

        if not len(callbacks):
            event._event.set()
            return

        self.run_callbacks(event, callbacks)

    def run_callbacks(self, event, callbacks):
        remove_list = []

        for callback, i in zip(callbacks, range(len(callbacks))):
            try:
                if callback(event, *event.args, **event.kwargs) is False:
                    remove_list.append(i)
            except:
                traceback.print_exc()

        with self._callbacks_lock:
            for i, j in zip(remove_list, range(len(remove_list))):
                callbacks.pop(i - j)

        event._event.set()

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

    def _emit_event(self, event_name, *args, **kwargs):
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

    def emit_event(self, event_name, *args, **kwargs):
        self._emit_event("event", event_name, *args, **kwargs)
        self._emit_event(event_name, *args, **kwargs)
