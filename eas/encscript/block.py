#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .namespace import Namespace

class Block(object):
    def __init__(self, args, body, parent_namespace=None):
        self.args = args
        self.body = body
        self.retcode = 0
        self.line_num = 0
        self.char_num = 0

        self.namespace = Namespace(parent_namespace)

    def begin(self, *args, **kwargs):
        raise NotImplementedError

    def evaluate_body(self, *args, **kwargs):
        for i in self.body:
            self.retcode = i.evaluate(*args, **kwargs)

    def end(self, *args, **kwargs):
        raise NotImplementedError

    def evaluate(self, *args, **kwargs):
        self.begin(*args, **kwargs)
        self.evaluate_body(*args, **kwargs)
        self.end(*args, **kwargs)

        return self.retcode
