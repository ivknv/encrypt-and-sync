# -*- coding: utf-8 -*-

from .logging import logger, SynchronizerFailLogReceiver
from ..log_receiver import LogReceiver
from ..target_manager import TargetManager

__all__ = ["Synchronizer"]

class Synchronizer(TargetManager):
    def __init__(self, *args, **kwargs):
        TargetManager.__init__(self, *args, **kwargs)

        self.add_receiver(LogReceiver(logger))
        self.add_receiver(SynchronizerFailLogReceiver())
