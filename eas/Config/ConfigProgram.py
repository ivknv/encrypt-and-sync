#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..EncScript import Program, Block, SysCommand, AndOperator
from ..EncScript.Exceptions import EvaluationError
from .ConfigNamespace import ConfigNamespace
from .ConfigBlock import ConfigBlock

class ConfigProgram(Program):
    def __init__(self, body):
        Program.__init__(self, body)

        self.namespace = ConfigNamespace()

    def evaluate_body(self, config):
        for i in self.body:
            if isinstance(i, SysCommand):
                raise EvaluationError(self, "Can't execute system commands")
            elif isinstance(i, Block) and not isinstance(i, ConfigBlock):
                raise EvaluationError(self, "Can't execute this kind of block")
            elif isinstance(i, AndOperator):
                raise EvaluationError(self, "'&&' operator is not available")

            i.evaluate(config)

    def evaluate(self, config):
        Program.evaluate(self, config)
