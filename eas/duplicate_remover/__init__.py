# -*- coding: utf-8 -*-

__all__ = ["DuplicateRemover", "DuplicateRemoverTarget", "DuplicateRemoverTask",
           "DuplicateRemoverWorker"]

from .duplicate_remover import DuplicateRemover
from .target import DuplicateRemoverTarget
from .task import DuplicateRemoverTask
from .worker import DuplicateRemoverWorker
