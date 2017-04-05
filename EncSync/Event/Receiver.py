#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import traceback

from .Event import Event

class Receiver(object):
    def __init__(self):
        self._callbacks = {}
        self._callbacks_lock = threading.Lock()

        self._active = True

    def add_callback(self, event_name, callback):
        with self._callbacks_lock:
            if event_name not in self._callbacks:
                self._callbacks[event_name] = [callback]
            else:
                self._callbacks[event_name].append(callback)

    def activate(self):
        self._active = True

    def deactivate(self):
        self._activate = False

    def is_active(self):
        return self._active

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

class ReceiverThread(Receiver, threading.Thread):
    def __init__(self, daemon=True):
        Receiver.__init__(self)
        threading.Thread.__init__(self, daemon=daemon)

        self._queue = []
        self._queue_lock = threading.Lock()

        self._dirty = threading.Event()

        self._stopped = False

    def stop(self):
        self._stopped = True
        self.deactivate()

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
                try:
                    event = self._queue.pop(0)
                except IndexError:
                    self._dirty.clear()
                    continue

            try:
                self.handle_event(event)
            except:
                traceback.print_exc()
