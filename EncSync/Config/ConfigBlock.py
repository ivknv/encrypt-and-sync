#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..EncScript import Block, SysCommand, AndOperator

__all__ = ["ConfigBlock"]

class ConfigBlock(Block):
    def evaluate_body(self, *args, **kwargs):
        for i in self.body:
            if isinstance(i, SysCommand):
                raise ValueError("Can't execute system commands")
            elif isinstance(i, Block) and not isinstance(i, ConfigBlock):
                raise ValueError("Can't execute this kind of block")
            elif isinstance(i, AndOperator):
                raise ValueError("'&&' operator is not available")

            self.retcode = i.evaluate(*args, **kwargs)
