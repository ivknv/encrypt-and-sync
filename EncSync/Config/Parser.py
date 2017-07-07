#!/usr/bin/env python
# -*- coding: utf-8 -*-

import enum

from .Tokenizer import Tokenizer, Token

class AST(object):
    class Type(enum.Enum):
        UNDEFINED  = 0
        CONFIG     = 1
        COMMAND    = 2
        BLOCK      = 3
        WORD       = 4
        LCBR       = 5
        RCBR       = 6
        SEP        = 7
        END        = 8

    def __init__(self, node_type=Type.UNDEFINED, token=None):
        self.type = node_type
        self.token = token
        self.children = []

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
        self.idx = 0

    def reset(self):
        self.idx = 0
        self.tokens = []

    def parse(self, output=None):
        if output is None:
            output = AST()

        self.parse_config(output)

        return output

    def parse_config(self, output):
        output.type = AST.Type.CONFIG

        while not self.accept(Token.Type.END):
            self.expect(Token.Type.WORD, Token.Type.SEP)

            if self.accept(Token.Type.WORD):
                self.parse_block_or_command(output.new_child())
            elif self.accept(Token.Type.SEP):
                self.parse_command(output.new_child())

        self.parse_end(output.new_child())

    def expect(self, *expected_types):
        if self.tokens[self.idx].type not in expected_types:
            raise ValueError("Unexpected token: %r" % self.tokens[self.idx])

    def accept(self, *expected_types):
        return self.tokens[self.idx].type in expected_types

    def parse_command(self, output):
        output.type = AST.Type.COMMAND

        while True:
            self.expect(Token.Type.WORD, Token.Type.SEP, Token.Type.END)

            if self.accept(Token.Type.END):
                break

            child = output.new_child()

            if self.accept(Token.Type.WORD):
                self.parse_word(child)
            elif self.accept(Token.Type.SEP):
                self.parse_sep(child)
                break

    def parse_block_or_command(self, output):
        output.type = AST.Type.BLOCK

        self.expect(Token.Type.WORD)

        while True:
            try:
                self.expect(Token.Type.WORD, Token.Type.LCBR)
            except ValueError as e:
                if not self.accept(Token.Type.SEP, Token.Type.END):
                    raise e
                output.type = AST.Type.COMMAND
                self.parse_command(output)
                return

            child = output.new_child()

            if self.accept(Token.Type.WORD):
                self.parse_word(child)
            elif self.accept(Token.Type.LCBR):
                self.parse_lcbr(child)
                break

        while True:
            self.expect(Token.Type.WORD, Token.Type.SEP, Token.Type.RCBR)

            child = output.new_child()

            if self.accept(Token.Type.WORD):
                self.parse_block_or_command(child)
            elif self.accept(Token.Type.SEP):
                self.parse_command(child)
            elif self.accept(Token.Type.RCBR):
                self.parse_rcbr(child)
                break

    def parse_token(self, token_type, ast_type, output):
        self.expect(token_type)

        output.type = ast_type
        output.token = self.tokens[self.idx]

        self.idx += 1

    def parse_sep(self, output):
        self.parse_token(Token.Type.SEP, AST.Type.SEP, output)

    def parse_word(self, output):
        self.parse_token(Token.Type.WORD, AST.Type.WORD, output)

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
