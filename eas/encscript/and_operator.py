#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .operator import Operator

class AndOperator(Operator):
    def evaluate(self, *args, **kwargs):
        ret = self.A.evaluate(*args, **kwargs)

        if ret:
            return ret

        return self.B.evaluate(*args, **kwargs)
