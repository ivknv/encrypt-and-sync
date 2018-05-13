#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .exceptions import UnknownCommandError, NotACommandError
from .exceptions import UnknownBlockError, NotABlockError
from .parser import AST
from .sys_command import SysCommand
from .and_operator import AndOperator
from .block import Block
from .command import Command

def ast2program(ast, program):
    program.body.clear()

    program.line_num = ast.line_num
    program.char_num = ast.char_num

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
                raise UnknownCommandError(ast, "Unknown command: %r" % args[0])

            command = command_type(args)
            command.line_num = ast.line_num
            command.char_num = ast.char_num

            if not isinstance(command, Command):
                raise NotACommandError(ast, "%r is not a command" % args[0])

            operator.A = command
        elif child.type == AST.Type.COMMAND:
            operator.B = ast2command(child, namespace)

            return operator

    if not args:
        return None

    try:
        command_type = namespace[args[0]]
    except KeyError:
        raise UnknownCommandError(ast, "Unknown command: %r" % args[0])

    if not issubclass(command_type, Command):
        raise NotACommandError(ast, "%r is not a command" % args[0])

    command = command_type(args)
    command.line_num = ast.line_num
    command.char_num = ast.char_num

    return command

def ast2syscommand(ast):
    sys_command = SysCommand(ast.token.string)
    sys_command.line_num = ast.line_num
    sys_command.char_num = ast.char_num

    return sys_command

def ast2operator(ast):
    if ast.children[0].type == AST.Type.AND:
        op = AndOperator(None, None)
        op.line_num = ast.line_num
        op.char_num = ast.char_num

        return op

def ast2block(ast, namespace):
    args = []
    body = []

    block = None

    for child in ast.children:
        if child.type == AST.Type.LCBR and block is None:
            try:
                block_type = namespace[""]
            except KeyError:
                raise UnknownBlockError(ast, "Unknown block: ''")

            if not issubclass(block_type, Block):
                raise NotABlockError(ast, "'' is not a block")

            args.append("")

            block = block_type(args, body, namespace)
            block.line_num = ast.line_num
            block.char_num = ast.char_num
        elif child.type == AST.Type.WORD:
            if not args:
                try:
                    block_type = namespace[child.token.string]
                except KeyError:
                    raise UnknownBlockError(ast, "Unknown block: %r" % child.token.string)

                if not issubclass(block_type, Block):
                    raise NotABlockError(ast, "%r is not a block" % child.token.string)

                block = block_type(args, body, namespace)
                block.line_num = ast.line_num
                block.char_num = ast.char_num

            args.append(child.token.string)
        elif child.type == AST.Type.ACTION:
            action = ast2action(child, block.namespace)

            if action is not None:
                body.append(action)

    return block
