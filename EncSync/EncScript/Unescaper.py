# -*- coding: utf-8 -*-

import enum

__all__ = ["Unescaper", "unescape_word"]

class State(enum.Enum):
    INITIAL   = 0
    DOLLAR    = 1
    QUOTES    = 2
    CQUOTES   = 3

class Unescaper(object):
    escape_map = {"'":  "'",
                  "\"": "\"",
                  "$": "$",
                  "a":  "\a",
                  "b":  "\b",
                  "e":  "\033",
                  "f":  "\f",
                  "n":  "\n",
                  "r":  "\r",
                  "t":  "\t",
                  "v":  "\v",
                  "\n": ""}

    def __init__(self, string):
        self.string = string
        self.idx = 0

    def read(self, size):
        result = self.string[self.idx:self.idx + size]
        self.idx += len(result)

        return result

    def read_target(self, size, target):
        result = ""

        while len(result) < size:
            c = self.read(1)

            if not c:
                break

            if not target(c):
                self.idx -= 1
                break

            result += c

        return result

    def read_hex(self, size):
        number = self.read_target(size, lambda x: x.isdigit() or x.lower() in "abcdef")

        if not number:
            raise ValueError("Empty hexadecimal")

        return int(number, 16)

    def read_oct(self, size):
        number = self.read_target(size, lambda x: x in "01234567")

        if not number:
            raise ValueError("Empty octal")

        return int(number, 8)

    def unescape_word(self):
        state = State.INITIAL
        escape = False
        quote_char = None

        while True:
            char = self.read(1)

            if not char:
                break

            if escape and state != State.CQUOTES:
                if char in ("'", '"', "$"):
                    yield char
                elif char != "\n":
                    yield "\\"
                    yield char

                escape = False

                continue

            if state == State.INITIAL:
                if char == "\\":
                    escape = True
                elif char in ('"', "'"):
                    state = State.QUOTES
                    quote_char = char
                elif char == "$":
                    state = State.DOLLAR
                else:
                    yield char
            elif state == State.DOLLAR:
                if char in ("'", '"'):
                    state = State.CQUOTES
                    quote_char = char
                elif char == "\\":
                    yield "$"

                    escape = True
                    state = State.INITIAL
                else:
                    state = State.INITIAL
                    yield "$"
                    yield char
            elif state == State.QUOTES:
                if char == "\\":
                    escape = True
                elif char == quote_char:
                    state = State.INITIAL
                else:
                    yield char
            elif state == State.CQUOTES:
                if escape:
                    if char in self.escape_map:
                        yield self.escape_map[char]
                    elif char == "u":
                        try:
                            number = self.read_hex(4)

                            try:
                                yield chr(number)
                            except ValueError:
                                yield "\uFFFD"
                        except ValueError:
                            yield r"\u"
                    elif char == "U":
                        try:
                            number = self.read_hex(8)

                            try:
                                yield chr(number)
                            except ValueError:
                                yield "\uFFFD"
                        except ValueError:
                            yield r"\U"
                    elif char == "x":
                        try:
                            number = self.read_hex(2)

                            try:
                                yield chr(number)
                            except ValueError:
                                yield "\uFFFD"
                        except ValueError:
                            yield r"\x"
                    elif char in "01234567":
                        self.idx -= 1

                        try:
                            number = self.read_oct(3)

                            try:
                                yield chr(number)
                            except ValueError:
                                yield "\uFFFD"
                        except ValueError:
                            yield "\\"
                            yield char
                    elif char != "\n":
                        yield "\\"
                        yield char

                    escape = False

                    continue
                
                if char == "\\":
                    escape = True
                elif char == quote_char:
                    state = State.INITIAL
                else:
                    yield char

        if state == State.DOLLAR:
            yield "$"
        elif escape:
            yield "\\"

def unescape_word(word):
    return "".join(Unescaper(word).unescape_word())
