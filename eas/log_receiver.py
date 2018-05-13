#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .events import Receiver

__all__ = ["LogReceiver"]

class LogReceiver(Receiver):
    def __init__(self, logger):
        Receiver.__init__(self)

        self.logger = logger

    def on_error(self, event, exception):
        self.logger.exception("An error occured")
