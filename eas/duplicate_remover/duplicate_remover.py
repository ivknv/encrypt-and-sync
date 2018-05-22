# -*- coding: utf-8 -*-

from ..target_manager import TargetManager
from ..log_receiver import LogReceiver
from .logging import logger

__all__ = ["DuplicateRemover"]

class DuplicateRemover(TargetManager):
    """
        Events: next_target, error
    """

    def __init__(self, *args, **kwargs):
        TargetManager.__init__(self, *args, **kwargs)

        self.add_receiver(LogReceiver(logger))
