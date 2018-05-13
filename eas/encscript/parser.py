#!/usr/bin/env python
# -*- coding: utf-8 -*-

import enum

from .tokenizer import Tokenizer, Token
from .exceptions import UnexpectedTokenError

__all__ = ["AST", "Parser"]

class AST(object):
    class Type(enum.Enum):
        UNDEFINED  = 0
        PROGRAM    = 1
        COMMAND    = 2
        BLOCK      = 3
        ACTION     = 4
        WORD       = 5
        SYSCOMMAND = 6
        OPERATOR   = 7
        AND        = 8
        LCBR       = 9
        RCBR       = 10
        SEP        = 11
        END        = 12

    def __init__(self, node_type=Type.UNDEFINED, token=None):
        self.type = node_type
        self.token = token
        self.children = []
        self.line_num = 0
        self.char_num = 0

    def set_nums(self):
        if self.token is not None:
            self.line_num = self.token.line_num
            self.char_num = self.token.char_num
        else:
            try:
                self.line_num = self.children[0].line_num
                self.char_num = self.children[0].char_num
            except IndexError:
                self.line_num = 1
                self.char_num = 1

    def new_child(self, *args, **kwargs):
        child = AST(*args, **kwargs)
        self.children.append(child)
        return child

    def __repr__(self):
        return "<AST type=%s children=%d>" % (self.type, len(self.children))

    def print(self, indent=0):
        print(" " * indent + repr(self))

        for i in self.children:
            i.print(indent + 2)

class Parser(object):
    def __init__(self, tokens=None):
        if tokens is None:
            tokens = []

        self.tokens = tokens
        self.path = None
        self.idx = 0

    def reset_state(self):
        self.idx = 0
        self.tokens = []

    def reset(self):
        self.reset_state()
        self.path = None

    def parse(self, output=None):
        if output is None:
            output = AST()

        self.parse_program(output)

        return output

    def parse_program(self, output):
        output.type = AST.Type.PROGRAM

        while not self.accept(Token.Type.END):
            self.parse_action(output.new_child())

        self.parse_end(output.new_child())

        output.set_nums()

    def expect(self, *expected_types):
        token = self.tokens[self.idx]

        if token.type not in expected_types:
            raise UnexpectedTokenError(self.path, token.line_num, token.char_num,
                                       "unexpected token: %r" % token)

    def accept(self, *expected_types):
        return self.tokens[self.idx].type in expected_types

    def parse_command(self, output, after_block=False):
        output.type = AST.Type.COMMAND

        expected = {Token.Type.WORD, Token.Type.SYSCOMMAND,
                    Token.Type.SEP, Token.Type.END}

        if after_block:
            expected.add(Token.Type.AND)
            expected.discard(Token.Type.SYSCOMMAND)

        while True:
            self.expect(*expected)

            if self.accept(Token.Type.END):
                break

            child = output.new_child()

            if self.accept(Token.Type.WORD):
                expected.discard(Token.Type.SYSCOMMAND)
                expected.add(Token.Type.AND)
                self.parse_word(child)
            elif self.accept(Token.Type.SYSCOMMAND):
                expected.discard(Token.Type.SYSCOMMAND)
                expected.discard(Token.Type.WORD)
                expected.add(Token.Type.AND)
                self.parse_syscommand(child)
            elif self.accept(Token.Type.AND):
                expected.discard(Token.Type.SEP)
                self.parse_operator(child)
                self.parse_command(output.new_child())
                break
            elif self.accept(Token.Type.SEP):
                self.parse_sep(child)
                break

        output.set_nums()

    def parse_block_or_command(self, output):
        output.type = AST.Type.BLOCK

        self.expect(Token.Type.WORD)

        while True:
            try:
                self.expect(Token.Type.WORD, Token.Type.LCBR)
            except UnexpectedTokenError as e:
                if not self.accept(Token.Type.AND, Token.Type.SEP, Token.Type.END):
                    raise e
                output.type = AST.Type.COMMAND
                self.parse_command(output, after_block=True)
                return

            child = output.new_child()

            if self.accept(Token.Type.WORD):
                self.parse_word(child)
            elif self.accept(Token.Type.LCBR):
                self.parse_lcbr(child)
                break

        while True:
            child = output.new_child()

            if self.accept(Token.Type.RCBR):
                self.parse_rcbr(child)
                break

            self.parse_action(child)

        output.set_nums()

    def parse_action(self, output):
        output.type = AST.Type.ACTION

        self.expect(Token.Type.WORD, Token.Type.SEP, Token.Type.SYSCOMMAND)

        child = output.new_child()

        if self.accept(Token.Type.WORD):
            self.parse_block_or_command(child)
        elif self.accept(Token.Type.SYSCOMMAND, Token.Type.SEP):
            self.parse_command(child)

        output.set_nums()

    def parse_operator(self, output):
        output.type = AST.Type.OPERATOR

        self.parse_and(output.new_child())

    def parse_token(self, token_type, ast_type, output):
        self.expect(token_type)

        output.type = ast_type
        output.token = self.tokens[self.idx]
        output.set_nums()

        self.idx += 1

    def parse_sep(self, output):
        self.parse_token(Token.Type.SEP, AST.Type.SEP, output)

    def parse_word(self, output):
        self.parse_token(Token.Type.WORD, AST.Type.WORD, output)

    def parse_syscommand(self, output):
        self.parse_token(Token.Type.SYSCOMMAND, AST.Type.SYSCOMMAND, output)

    def parse_and(self, output):
        self.parse_token(Token.Type.AND, AST.Type.AND, output)

    def parse_lcbr(self, output):
        self.parse_token(Token.Type.LCBR, AST.Type.LCBR, output)

    def parse_rcbr(self, output):
        self.parse_token(Token.Type.RCBR, AST.Type.RCBR, output)

    def parse_end(self, output):
        self.parse_token(Token.Type.END, AST.Type.END, output)

def parse(string, output=None):
    tokenizer = Tokenizer()
    parser = Parser()

    tokenizer.parse_string(string, parser.tokens)
    tokenizer.end(parser.tokens)

    return parser.parse(output)
