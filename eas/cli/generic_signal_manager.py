#!/usr/bin/env python
# -*- coding: utf-8 -*-

import signal
import sys

from .signal_manager import SignalManager

__all__ = ["GenericSignalManager"]

def _exit(signum):
    sys.exit(128 + signum)

class GenericSignalManager(SignalManager):
    def __init__(self, target_manager):
        SignalManager.__init__(self)

        def quit_handler(signum, frame):
            target_manager.change_status("suspended")
            target_manager.full_stop()
            _exit(signum)

        for sigstr in ("SIGINT", "SIGTERM", "SIGHUP"):
            if hasattr(signal, sigstr):
                signum = getattr(signal, sigstr)
                self.set(signum, quit_handler)
