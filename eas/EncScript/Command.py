#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Command(object):
    def __init__(self, args):
        self.args = args
        self.line_num = 0
        self.char_num = 0

    def evaluate(self, *args, **kwargs):
        raise NotImplementedError
