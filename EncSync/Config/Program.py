#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Parser import AST
from .Namespace import Namespace
from .Block import Block, ast2block
from .Command import ast2command

class Program(Block):
    def __init__(self, body):
        Block.__init__(self, [], body)

    def begin(self, *args, **kwargs): pass
    def end(self, *args, **kwargs): pass

def ast2program(ast, program):
    body = program.body
    body.clear()

    for child in ast.children:
        assert(child.type in (AST.Type.COMMAND, AST.Type.BLOCK, AST.Type.END))

        if child.type == AST.Type.COMMAND:
            command = ast2command(child, program.namespace)
            if command is not None:
                body.append(command)
        elif child.type == AST.Type.BLOCK:
            body.append(ast2block(child, program.namespace))

    return program
