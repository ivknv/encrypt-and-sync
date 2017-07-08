#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Parser import AST
from .Namespace import Namespace
from .Command import ast2command

class Block(object):
    def __init__(self, args, body, parent_namespace=None):
        self.args = args
        self.body = body

        self.namespace = Namespace(parent_namespace)

    def begin(self, *args, **kwargs):
        raise NotImplementedError

    def evaluate_body(self, *args, **kwargs):
        for i in self.body:
            i.evaluate(*args, **kwargs)

    def end(self, *args, **kwargs):
        raise NotImplementedError

    def evaluate(self, *args, **kwargs):
        self.begin(*args, **kwargs)
        self.evaluate_body(*args, **kwargs)
        self.end(*args, **kwargs)

def ast2block(ast, namespace):
    args = []
    body = []

    block = None

    for child in ast.children:
        assert(child.type in (AST.Type.WORD,
                              AST.Type.LCBR,
                              AST.Type.COMMAND,
                              AST.Type.BLOCK,
                              AST.Type.RCBR))

        if child.type == AST.Type.LCBR and block is None:
            block = namespace[""](args, body, namespace)
            args.append("")

        if child.type == AST.Type.WORD:
            if not args:
                block = namespace[child.token.string](args, body, namespace)

            args.append(child.token.string)
        elif child.type == AST.Type.COMMAND:
            command = ast2command(child, block.namespace)
            if command is not None:
                body.append(command)
        elif child.type == AST.Type.BLOCK:
            body.append(ast2block(child, block.namespace))

    return block
