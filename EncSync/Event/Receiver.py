#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import traceback
import weakref

from .Event import Event

__all__ = ["Receiver"]

class Receiver(object):
    def __init__(self):
        self._callbacks = {}
        self._callbacks_lock = threading.RLock()

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
