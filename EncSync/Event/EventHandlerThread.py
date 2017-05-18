#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import traceback

from ..Worker import Worker

from .Event import Event

# Worker is already a subclass of EventHandler
class EventHandlerThread(Worker):
    def __init__(self, parent=None, daemon=True):
        Worker.__init__(self, parent, daemon)

        self._queue = []
        self._queue_lock = threading.Lock()

        self._dirty = threading.Event()

    def receive(self, emitter, event_name, *args, **kwargs):
        with self._queue_lock:
            event = Event(emitter, self, event_name, args, kwargs)
            self._queue.append(event)

            self._dirty.set()

            return event

    def run(self):
        self._dirty.set()

        while not self.stopped:
            self._dirty.wait()

            with self._queue_lock:
                if self.stopped:
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
