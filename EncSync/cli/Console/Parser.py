#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Tokenizer import Tokenizer, Token

class AST(object):
    UNDEFINED  = 0
    PROGRAM    = 1
    COMMAND    = 2
    SYSCOMMAND = 3
    WORD       = 4
    SEP        = 5
    END        = 6

    def __init__(self, node_type=None, token=None):
        if node_type is None:
            node_type = AST.UNDEFINED

        self.type = node_type
        self.token = token
        self.children = []

    def __repr__(self):
        types = {AST.UNDEFINED:  "UNDEFINED",
                 AST.PROGRAM:    "PROGRAM",
                 AST.COMMAND:    "COMMAND",
                 AST.SYSCOMMAND: "SYSCOMMAND",
                 AST.WORD:       "WORD",
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

        self.parse_program(output)

        return output

    def parse_program(self, output):
        output.type = AST.PROGRAM

        while self.tokens[self.idx].type != Token.END:
            token = self.tokens[self.idx]

            if token.type == Token.SYSCOMMAND:
                child = AST()
                output.children.append(child)

                self.parse_syscommand(child)
            elif token.type in (Token.WORD, Token.SEP):
                child = AST()
                output.children.append(child)

                self.parse_command(child)
            else:
                assert(False)

        child = AST()
        output.children.append(child)

        self.parse_end(child)

    def parse_syscommand(self, output):
        output.type = AST.SYSCOMMAND
        output.token = self.tokens[self.idx]

        self.idx += 1

    def parse_command(self, output):
        output.type = AST.COMMAND

        while True:
            token = self.tokens[self.idx]

            if token.type == Token.WORD:
                child = AST()
                output.children.append(child)

                self.parse_word(child)
            elif token.type == Token.SEP:
                child = AST()
                output.children.append(child)

                self.parse_sep(child)

                break
            elif token.type == Token.END:
                break

    def parse_sep(self, output):
        output.type = AST.SEP
        output.token = self.tokens[self.idx]

        self.idx += 1

    def parse_word(self, output):
        output.type = AST.WORD
        output.token = self.tokens[self.idx]

        self.idx += 1

    def parse_end(self, output):
        output.type = AST.END
        output.token = self.tokens[self.idx]

        self.idx += 1

def parse(string, output=None):
    tokenizer = Tokenizer()
    parser = Parser()

    tokenizer.parse_string(string, parser.tokens)
    tokenizer.end(parser.tokens)

    return parser.parse(output)
