#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..encscript import Block, SysCommand, AndOperator
from ..encscript.exceptions import EvaluationError

__all__ = ["ConfigBlock"]

class ConfigBlock(Block):
    def evaluate_body(self, *args, **kwargs):
        for i in self.body:
            if isinstance(i, SysCommand):
                raise EvaluationError(self, "Can't execute system commands")
            elif isinstance(i, Block) and not isinstance(i, ConfigBlock):
                raise EvaluationError(self, "Can't execute this kind of block")
            elif isinstance(i, AndOperator):
                raise EvaluationError(self, "'&&' operator is not available")

            self.retcode = i.evaluate(*args, **kwargs)
