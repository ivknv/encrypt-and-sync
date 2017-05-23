#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Tokenizer import Tokenizer, Token

class AST(object):
    UNDEFINED   = 0
    PROGRAM     = 1
    COMMAND     = 2
    SYSCOMMAND  = 3
    ANDOPERATOR = 4
    WORD        = 5
    SEP         = 6
    END         = 7

    def __init__(self, node_type=None, token=None):
        if node_type is None:
            node_type = AST.UNDEFINED

        self.type = node_type
        self.token = token
        self.children = []

    def __repr__(self):
        types = {AST.UNDEFINED:   "UNDEFINED",
                 AST.PROGRAM:     "PROGRAM",
                 AST.COMMAND:     "COMMAND",
                 AST.SYSCOMMAND:  "SYSCOMMAND",
                 AST.ANDOPERATOR: "ANDOPERATOR",
                 AST.WORD:        "WORD",
                 AST.SEP:         "SEP",
                 AST.END:         "END"}

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

        self.parse_program(output)

        return output

    def parse_program(self, output):
        output.type = AST.PROGRAM

        while not self.accept(Token.END):
            self.expect(Token.WORD, Token.SEP, Token.SYSCOMMAND)

            if self.accept(Token.SYSCOMMAND):
                child = AST()
                output.children.append(child)

                self.parse_syscommand(child)
            elif self.accept(Token.WORD, Token.SEP):
                child = AST()
                output.children.append(child)

                self.parse_command(child)

        child = AST()
        output.children.append(child)

        self.parse_end(child)

    def expect(self, *expected_types):
        if self.tokens[self.idx].type not in expected_types:
            raise ValueError("Unexpected token: %r" % self.tokens[self.idx])

    def accept(self, *expected_types):
        return self.tokens[self.idx].type in expected_types

    def parse_syscommand(self, output):
        self.expect(Token.SYSCOMMAND)

        output.type = AST.SYSCOMMAND
        output.token = self.tokens[self.idx]

        self.idx += 1

    def parse_command(self, output):
        output.type = AST.COMMAND

        expected_tokens = {Token.WORD, Token.SEP, Token.END}

        while True:
            self.expect(*expected_tokens)

            if self.accept(Token.WORD):
                expected_tokens.add(Token.ANDOPERATOR)

                child = AST()
                output.children.append(child)

                self.parse_word(child)
            elif self.accept(Token.SEP):
                child = AST()
                output.children.append(child)

                self.parse_sep(child)

                break
            elif self.accept(Token.END):
                break
            elif self.accept(Token.ANDOPERATOR):
                child = AST()
                output.children.append(child)

                self.parse_andoperator(child)

                self.expect(Token.WORD, Token.SYSCOMMAND, Token.SEP)

                child = AST()
                output.children.append(child)

                if self.accept(Token.SYSCOMMAND):
                    self.parse_syscommand(child)
                elif self.accept(Token.WORD):
                    self.parse_command(child)
                elif self.accept(Token.SEP):
                    self.parse_sep(child)

    def parse_andoperator(self, output):
        self.expect(Token.ANDOPERATOR)

        output.type = AST.ANDOPERATOR
        output.token = self.tokens[self.idx]

        self.idx += 1

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
