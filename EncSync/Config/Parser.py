#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Tokenizer import Tokenizer, Token

class AST(object):
    UNDEFINED  = 0
    CONFIG     = 1
    COMMAND    = 2
    BLOCK      = 3
    SIMPLEWORD = 4
    WORD       = 5
    LCBR       = 6
    RCBR       = 7
    SEP        = 8
    END        = 9

    def __init__(self, node_type=None, token=None):
        if node_type is None:
            node_type = AST.UNDEFINED

        self.type = node_type
        self.token = token
        self.children = []

    def __repr__(self):
        types = {AST.UNDEFINED:  "UNDEFINED",
                 AST.CONFIG:     "CONFIG",
                 AST.COMMAND:    "COMMAND",
                 AST.BLOCK:      "BLOCK",
                 AST.WORD:       "WORD",
                 AST.SIMPLEWORD: "SIMPLEWORD",
                 AST.LCBR:       "LCBR",
                 AST.RCBR:       "RCBR",
                 AST.SEP:        "SEP",
                 AST.END:        "END"}

        typestr = types.get(self.type, self.type)

        return "<AST type=%s children=%d>" % (typestr, len(self.children))

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
        output.type = AST.CONFIG

        while not self.accept(Token.END):
            self.expect(Token.SIMPLEWORD, Token.WORD, Token.SEP)

            if self.accept(Token.WORD, Token.SEP):
                child = AST()
                output.children.append(child)

                self.parse_command(child)
            elif self.accept(Token.SIMPLEWORD):
                child = AST()
                output.children.append(child)

                self.parse_block(child)

        child = AST()
        output.children.append(child)

        self.parse_end(child)

    def expect(self, *expected_types):
        if self.tokens[self.idx].type not in expected_types:
            raise ValueError("Unexpected token: %r" % self.tokens[self.idx])

    def accept(self, *expected_types):
        return self.tokens[self.idx].type in expected_types

    def parse_command(self, output):
        output.type = AST.COMMAND

        while True:
            self.expect(Token.SIMPLEWORD, Token.WORD, Token.SEP, Token.END)

            if self.accept(Token.END):
                break

            child = AST()
            output.children.append(child)

            if self.accept(Token.WORD):
                self.parse_word(child)
            elif self.accept(Token.SIMPLEWORD):
                self.parse_simpleword(child)
            elif self.accept(Token.SEP):
                self.parse_sep(child)
                break

    def parse_block(self, output):
        output.type = AST.BLOCK

        self.expect(Token.SIMPLEWORD)

        while True:
            try:
                self.expect(Token.WORD, Token.SIMPLEWORD, Token.LCBR)
            except ValueError as e:
                if not self.accept(Token.SEP, Token.END):
                    raise e
                output.type = AST.COMMAND
                self.parse_command(output)
                return

            child = AST()
            output.children.append(child)

            if self.accept(Token.WORD):
                self.parse_word(child)
            elif self.accept(Token.SIMPLEWORD):
                self.parse_simpleword(child)
            elif self.accept(Token.LCBR):
                self.parse_lcbr(child)
                break

        while True:
            self.expect(Token.WORD, Token.SIMPLEWORD, Token.SEP, Token.RCBR)

            child = AST()
            output.children.append(child)

            if self.accept(Token.WORD, Token.SIMPLEWORD, Token.SEP):
                self.parse_command(child)
            elif self.accept(Token.RCBR):
                self.parse_rcbr(child)
                break

    def parse_sep(self, output):
        self.expect(Token.SEP)

        output.type = AST.SEP
        output.token = self.tokens[self.idx]

        self.idx += 1

    def parse_word(self, output):
        self.expect(Token.WORD)

        output.type = AST.WORD
        output.token = self.tokens[self.idx]

        self.idx += 1

    def parse_simpleword(self, output):
        self.expect(Token.SIMPLEWORD)

        output.type = AST.SIMPLEWORD
        output.token = self.tokens[self.idx]

        self.idx += 1

    def parse_lcbr(self, output):
        self.expect(Token.LCBR)

        output.type = AST.LCBR
        output.token = self.tokens[self.idx]

        self.idx += 1

    def parse_rcbr(self, output):
        self.expect(Token.RCBR)

        output.type = AST.RCBR
        output.token = self.tokens[self.idx]

        self.idx += 1

    def parse_end(self, output):
        self.expect(Token.END)

        output.type = AST.END
        output.token = self.tokens[self.idx]

        self.idx += 1

def parse(string, output=None):
    tokenizer = Tokenizer()
    parser = Parser()

    tokenizer.parse_string(string, parser.tokens)
    tokenizer.end(parser.tokens)

    return parser.parse(output)
