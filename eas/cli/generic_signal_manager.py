# -*- coding: utf-8 -*-

import signal
import sys

from .signal_manager import SignalManager

__all__ = ["GenericSignalManager"]

def _exit(signum):
    sys.exit(128 + signum)

class GenericSignalManager(SignalManager):
    def __init__(self, target_runner):
        SignalManager.__init__(self)

        def quit_handler(signum, frame):
            target_runner.change_status("suspended")
            target_runner.stop()
            target = target_runner.cur_target

            if target is not None:
                target.pool.join()

            _exit(signum)

        for sigstr in ("SIGINT", "SIGTERM", "SIGHUP"):
            if hasattr(signal, sigstr):
                signum = getattr(signal, sigstr)
                self.set(signum, quit_handler)
