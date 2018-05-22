# -*- coding: utf-8 -*-

from .logging import logger
from ..target_runner import TargetRunner
from ..log_receiver import LogReceiver

__all__ = ["Downloader"]

class Downloader(TargetRunner):
    """
        Events: next_target, error
    """

    def __init__(self, *args, **kwargs):
        TargetRunner.__init__(self, *args, **kwargs)

        self.add_receiver(LogReceiver(logger))
