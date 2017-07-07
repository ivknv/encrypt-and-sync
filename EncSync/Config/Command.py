#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Parser import AST

class Command(object):
    def __init__(self, args):
        self.args = args

    def evaluate(self, *args, **kwargs):
        raise NotImplementedError

def ast2command(ast, namespace):
    args = []

    for child in ast.children:
        assert(child.type in (AST.Type.WORD, AST.Type.SEP))

        if child.type == AST.Type.WORD:
            args.append(child.token.string)

    if not args:
        return None

    return namespace[args[0]](args)
