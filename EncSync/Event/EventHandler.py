#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import traceback

from .Exceptions import UnknownEventError, DuplicateEventError
from .Event import Event

class EventHandler(object):
    def __init__(self):
        self._events = {}
        self._events_lock = threading.Lock()

        self._receivers = []
        self._receivers_lock = threading.Lock()

        self._callbacks = {}
        self._callbacks_lock = threading.Lock()

    def add_callback(self, event_name, callback):
        with self._callbacks_lock:
            if event_name not in self._callbacks:
                self._callbacks[event_name] = [callback]
            else:
                self._callbacks[event_name].append(callback)

    def receive(self, emitter, event_name, *args, **kwargs):
        event = Event(emitter, self, event_name, args, kwargs)

        self.handle_event(event)

        return event

    def get_callbacks(self, event_name):
        with self._callbacks_lock:
            return list(self._callbacks.get(event_name, []))

    def handle_event(self, event):
        callbacks = self.get_callbacks(event.name)

        if not len(callbacks):
            event._event.set()
            return

        self.run_callbacks(event, callbacks)

    def run_callbacks(self, event, callbacks):
        remove_list = []

        for callback, i in zip(callbacks, range(len(callbacks))):
            if callback(event, *event.args, **event.kwargs) is False:
                remove_list.append(i)

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
            self._receivers.append(receiver)

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

class EventHandlerThread(EventHandler, threading.Thread):
    def __init__(self, daemon=True):
        EventHandler.__init__(self)
        threading.Thread.__init__(self, daemon=daemon)

        self._queue = []
        self._queue_lock = threading.Lock()

        self._dirty = threading.Event()

        self._stopped = False

    def stop(self):
        self._stopped = True

    def is_stopped(self):
        return self._stopped

    def receive(self, emitter, event_name, *args, **kwargs):
        with self._queue_lock:
            event = Event(emitter, self, event_name, args, kwargs)
            self._queue.append(event)

            self._dirty.set()

            return event

    def run(self):
        self._dirty.set()

        while not self._stopped:
            self._dirty.wait()

            with self._queue_lock:
                if self._stopped:
                    break

                try:
                    event = self._queue.pop(0)
                except IndexError:
                    self._dirty.clear()
                    continue

            try:
                self.handle_event(event)
            except:
                traceback.print_exc()
