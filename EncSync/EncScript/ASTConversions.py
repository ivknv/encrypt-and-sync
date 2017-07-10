#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Parser import AST
from .SysCommand import SysCommand
from .AndOperator import AndOperator
from .Block import Block
from .Command import Command

def ast2program(ast, program):
    program.body.clear()

    for child in ast.children:
        if child.type == AST.Type.END:
            break

        action = ast2action(child, program.namespace)

        if action is not None:
            program.body.append(action)

    return program

def ast2action(ast, namespace):
    child = ast.children[0]

    if child.type == AST.Type.COMMAND:
        return ast2command(child, namespace)

    return ast2block(child, namespace)

def ast2command(ast, namespace):
    args = []

    operator = None

    for child in ast.children:
        if child.type == AST.Type.WORD:
            args.append(child.token.string)
        elif child.type == AST.Type.SYSCOMMAND:
            return ast2syscommand(child)
        elif child.type == AST.Type.OPERATOR:
            operator = ast2operator(child)

            try:
                command_type = namespace[args[0]]
            except KeyError:
                raise ValueError("Unknown command: %r" % args[0])

            if not issubclass(operator.A, Command):
                raise ValueError("%r is not a command" % args[0])

            operator.A = command_type(args)
        elif child.type == AST.Type.COMMAND:
            operator.B = ast2command(child, namespace)

            return operator

    if not args:
        return None

    try:
        command_type = namespace[args[0]]
    except KeyError:
        raise ValueError("Unknown command: %r" % args[0])

    if not issubclass(command_type, Command):
        raise ValueError("%r is not a command" % args[0])

    return command_type(args)

def ast2syscommand(ast):
    return SysCommand(ast.token.string)

def ast2operator(ast):
    if ast.children[0].type == AST.Type.AND:
        return AndOperator(None, None)

def ast2block(ast, namespace):
    args = []
    body = []

    block = None

    for child in ast.children:
        if child.type == AST.Type.LCBR and block is None:
            try:
                block_type = namespace[""]
            except KeyError:
                raise ValueError("Unknown block: ''")

            if not issubclass(block_type, Block):
                raise ValueError("'' is not a block")

            block = block_type(args, body, namespace)

            args.append("")

        if child.type == AST.Type.WORD:
            if not args:
                try:
                    block_type = namespace[child.token.string]
                except KeyError:
                    raise ValueError("Unknown block: %r" % child.token.string)

                if not issubclass(block_type, Block):
                    raise ValueError("%r is not a block" % child.token.string)

                block = block_type(args, body, namespace)

            args.append(child.token.string)
        elif child.type == AST.Type.ACTION:
            action = ast2action(child, block.namespace)

            if action is not None:
                body.append(action)

    return block
