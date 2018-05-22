# -*- coding: utf-8 -*-

from .logging import logger, SynchronizerFailLogReceiver
from ..log_receiver import LogReceiver
from ..target_runner import TargetRunner

__all__ = ["Synchronizer"]

class Synchronizer(TargetRunner):
    def __init__(self, *args, **kwargs):
        TargetRunner.__init__(self, *args, **kwargs)

        self.add_receiver(LogReceiver(logger))
        self.add_receiver(SynchronizerFailLogReceiver())
