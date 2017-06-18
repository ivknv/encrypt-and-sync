#!/usr/bin/env python
# -*- coding: utf-8 -*-

import signal
import sys

from ...SignalManager import SignalManager

def _exit(signum):
    sys.exit(128 + signum)

class GenericSignalManager(SignalManager):
    def __init__(self, target_manager):
        SignalManager.__init__(self)

        self.target_manager = target_manager

        for sigstr in ("SIGINT", "SIGTERM", "SIGHUP"):
            if hasattr(signal, sigstr):
                signum = getattr(signal, sigstr)
                self.set(signum, self.quit_handler)

    def _stop_target_manager(self):
        self.target_manager.change_status("suspended")
        self.target_manager.full_stop()

    def quit_handler(self, signum, frame):
        self._stop_target_manager()
        _exit(signum)
