#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .block import Block

class Program(Block):
    def __init__(self, body):
        Block.__init__(self, [], body)

    def begin(self, *args, **kwargs): pass
    def end(self, *args, **kwargs): pass
