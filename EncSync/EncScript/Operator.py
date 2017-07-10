#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Operator(object):
    def __init__(self, A, B):
        self.A, self.B = A, B

    def evaluate(self, *args, **kwargs):
        raise NotImplementedError
