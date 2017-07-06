#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Event.Receiver import Receiver

class LogReceiver(Receiver):
    def __init__(self, logger):
        Receiver.__init__(self)

        self.logger = logger

        self.add_callback("error", self.on_error)

    def on_error(self, event, exception):
        self.logger.exception("An error occured")
