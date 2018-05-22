# -*- coding: utf-8 -*-

from .logging import logger
from ..log_receiver import LogReceiver
from ..target_runner import TargetRunner

__all__ = ["Scanner"]

class Scanner(TargetRunner):
    """
        Events: next_target, error
    """

    def __init__(self, *args, **kwargs):
        TargetRunner.__init__(self, *args, **kwargs)

        self.add_receiver(LogReceiver(logger))
