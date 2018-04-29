#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Operator(object):
    def __init__(self, A, B):
        self.A, self.B = A, B
        self.line_num = 0
        self.char_num = 0

    def evaluate(self, *args, **kwargs):
        raise NotImplementedError
