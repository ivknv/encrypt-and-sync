# -*- coding: utf-8 -*-

import threading

__all__ = ["Emitter"]

class Emitter(object):
    def __init__(self):
        self._receivers = []
        self._receivers_lock = threading.RLock()

    def add_receiver(self, receiver):
        with self._receivers_lock:
            if receiver not in self._receivers:
                self._receivers.append(receiver)

    def remove_receiver(self, receiver):
        with self._receivers_lock:
            self._receivers.remove(receiver)

    def emit_event(self, event_name, *args, **kwargs):
        with self._receivers_lock:
            receivers = list(self._receivers)

        events = []

        for receiver in receivers:
            events.append(receiver.receive(self, event_name, *args, **kwargs))

        return events
