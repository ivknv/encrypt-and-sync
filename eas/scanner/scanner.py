# -*- coding: utf-8 -*-

from .logging import logger
from ..log_receiver import LogReceiver
from ..target_manager import TargetManager

__all__ = ["Scanner"]

class Scanner(TargetManager):
    """
        Events: next_target, error
    """

    def __init__(self, *args, **kwargs):
        TargetManager.__init__(self, *args, **kwargs)

        self.add_receiver(LogReceiver(logger))
