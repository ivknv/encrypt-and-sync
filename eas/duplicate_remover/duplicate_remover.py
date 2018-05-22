# -*- coding: utf-8 -*-

from ..target_runner import TargetRunner
from ..log_receiver import LogReceiver
from .logging import logger

__all__ = ["DuplicateRemover"]

class DuplicateRemover(TargetRunner):
    """
        Events: next_target, error
    """

    def __init__(self, *args, **kwargs):
        TargetRunner.__init__(self, *args, **kwargs)

        self.add_receiver(LogReceiver(logger))
