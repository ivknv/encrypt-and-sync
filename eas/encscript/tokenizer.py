#!/usr/bin/env python
# -*- coding: utf-8 -*-

import enum

from .unescaper import unescape_word
from .exceptions import UnexpectedCharacterError

__all__ = ["Tokenizer", "Token", "tokenize"]

class Token(object):
    class Type(enum.Enum):
        UNDEFINED  = 0
        WORD       = 1
        SYSCOMMAND = 2
        AND        = 3
        LCBR       = 4
        RCBR       = 5
        SEP        = 6
        END        = 7

    def __init__(self, string, token_type=Type.UNDEFINED, line_num=0, char_num=0):
        self.string = string
        self.type = token_type
        self.line_num = line_num
        self.char_num = char_num

    def __repr__(self):
        if self.string:
            return "<Token string=%r type=%s>" % (self.string, self.type)

        return "<Token type=%s>" % self.type

class Char(object):
    def __init__(self, char):
        self.char = char
        self.authentic = True

    def is_whitespace(self):
        if not self.authentic:
            return self.char in ("\r",)

        return self.char in (" ", "\r", "\n", "\t")

    def is_newline(self):
        return self.authentic and self.char == "\n"

    def is_separator(self):
        return self.authentic and self.char in (";", "\n")

    def is_quotes(self):
        if not self.authentic:
            return False

        return self.char in ("'", '"')

    def is_escape(self):
        return self.authentic and self.char == "\\"

    def is_lcbr(self):
        return self.authentic and self.char == "{"

    def is_rcbr(self):
        return self.authentic and self.char == "}"

    def is_comment(self):
        return self.authentic and self.char == "#"

    def is_excl(self):
        return self.authentic and self.char == "!"

    def is_ampersand(self):
        return self.authentic and self.char == "&"

    def __repr__(self):
        if self.authentic:
            return repr(self.char)

        return repr("\\" + self.char)

class State(enum.Enum):
    INITIAL    = 0
    WORD       = 1
    COMMENT    = 2
    QUOTES     = 3
    SYSCOMMAND = 4
    AND        = 5
    FINAL      = 6

class Tokenizer(object):
    def __init__(self):
        self.state = State.INITIAL
        self.cur_token = Token("", Token.Type.UNDEFINED, 1, 1)

        self.escape = False
        self.in_quotes = False

        self.quote_char = None

        self.char_num = 1
        self.line_num = 1
        self.path = None

        self.state_handlers = {State.INITIAL:    self._handle_initial,
                               State.WORD:       self._handle_word,
                               State.COMMENT:    self._handle_comment,
                               State.QUOTES:     self._handle_quotes,
                               State.SYSCOMMAND: self._handle_syscommand,
                               State.AND:        self._handle_and,
                               State.FINAL:      self._handle_final}

    def end(self, output):
        if self.escape:
            self.escape = False

            if self.cur_token.type == Token.Type.UNDEFINED:
                self.cur_token.type = Token.Type.WORD
            self.cur_token.string += "\\"
        self._push_token(output)

        self.cur_token.type = Token.Type.END
        self._push_token(output)

        self._change_state(State.FINAL)

    def reset_state(self):
        self.escape = False
        self._exit_quotes()
        self._change_state(State.INITIAL)
        self.cur_token = Token("", Token.Type.UNDEFINED, self.line_num, self.char_num)

    def reset(self):
        self.line_num = 0
        self.char_num = 0
        self.path = None

        self.reset_state()

    def parse_string(self, string, output=None):
        if output is None:
            output = []

        for c in string:
            self.next_char(c, output)

        return output

    def next_char(self, char, output):
        assert(self.state != State.FINAL)

        if isinstance(char, str):
            char = Char(char)

        if self.escape:
            char.authentic = False
        elif self.in_quotes and char.char not in (self.quote_char, "\\"):
            char.authentic = False

        if char.is_escape():
            self.escape = True
            self.char_num += 1
            return

        if char.char == "\n":
            self.char_num = 1
            self.line_num += 1

        self.state_handlers[self.state](char, output)

        if char.char != "\n":
            self.char_num += 1

        self.escape = False

    def _change_state(self, new_state):
        self.state = new_state

    def _enter_quotes(self, quote_char):
        self.in_quotes = True
        self.quote_char = quote_char

    def _exit_quotes(self):
        self.in_quotes = False
        self.quote_char = None

    def _push_token(self, output):
        if self.cur_token.type != Token.Type.UNDEFINED:
            if self.cur_token.type == Token.Type.WORD:
                self.cur_token.string = unescape_word(self.cur_token.string)

            output.append(self.cur_token)

        self.cur_token = Token("", Token.Type.UNDEFINED, self.line_num, self.char_num)

    def _handle_initial(self, char, output):
        self.cur_token.char_num = self.char_num
        self.cur_token.line_num = self.line_num

        if char.is_whitespace():
            return

        if char.is_comment():
            self._change_state(State.COMMENT)
            return

        if char.is_quotes():
            self.cur_token.type = Token.Type.WORD
            self.cur_token.string += char.char

            self._enter_quotes(char.char)
            self._change_state(State.QUOTES)
        elif char.is_separator():
            self.cur_token.type = Token.Type.SEP
            self.cur_token.string += char.char

            self._push_token(output)
        elif char.is_lcbr():
            self.cur_token.type = Token.Type.LCBR
            self.cur_token.string = char.char

            self._push_token(output)
        elif char.is_rcbr():
            self.cur_token.type = Token.Type.RCBR
            self.cur_token.string = char.char

            self._push_token(output)
        elif char.is_excl():
            self.cur_token.type = Token.Type.SYSCOMMAND
            self._change_state(State.SYSCOMMAND)
        elif char.is_ampersand():
            raise UnexpectedCharacterError(self.path, self.line_num, self.char_num,
                                           "unexpected '&' character")
        else:
            self.cur_token.type = Token.Type.WORD

            if self.escape and char.char in ("\\", "'", '"', "$", "\n"):
                self.cur_token.string += "\\"

            self.cur_token.string += char.char

            self._change_state(State.WORD)

    def _handle_word(self, char, output):
        if char.is_comment():
            self._push_token(output)
            self._change_state(State.COMMENT)
        elif char.is_quotes():
            self.cur_token.string += char.char
            self.cur_token.type = Token.Type.WORD

            self._enter_quotes(char.char)
            self._change_state(State.QUOTES)
        elif char.is_separator():
            self._push_token(output)

            self.cur_token.type = Token.Type.SEP
            self.cur_token.string += char.char

            self._push_token(output)
            self._change_state(State.INITIAL)
        elif char.is_whitespace():
            self._push_token(output)
        elif char.is_lcbr():
            self._push_token(output)

            if self.cur_token.string:
                return

            self.cur_token.type = Token.Type.LCBR
            self.cur_token.string = char.char

            self._push_token(output)
            self._change_state(State.INITIAL)
        elif char.is_rcbr():
            self._push_token(output)

            if self.cur_token.string:
                return

            self.cur_token.type = Token.Type.RCBR
            self.cur_token.string = char.char

            self._push_token(output)
            self._change_state(State.INITIAL)
        elif char.is_ampersand():
            self._push_token(output)

            self.cur_token.type = Token.Type.AND
            self.cur_token.string = char.char

            self._change_state(State.AND)
        else:
            self.cur_token.type = Token.Type.WORD

            if self.escape and char.char in ("\\", "'", '"', "$", "\n"):
                self.cur_token.string += "\\"

            self.cur_token.string += char.char

    def _handle_comment(self, char, output):
        if char.is_newline():
            self._change_state(State.INITIAL)

    def _handle_quotes(self, char, output):
        if char.is_quotes() and self.in_quotes and char.char == self.quote_char:
            self.cur_token.string += char.char
            self._exit_quotes()
            self._change_state(State.WORD)
        else:
            self.cur_token.type = Token.Type.WORD
            if self.escape:
                self.cur_token.string += "\\"

            self.cur_token.string += char.char

    def _handle_syscommand(self, char, output):
        if char.is_newline():
            self._push_token(output)
            self._change_state(State.INITIAL)
            return

        self.cur_token.string += char.char

    def _handle_and(self, char, output):
        if not char.is_ampersand():
            msg = "expected '&', got %r instead" % (char.char,)
            raise UnexpectedCharacterError(self.path, self.line_num, self.char_num, msg)

        self.cur_token.string += char.char
        self._push_token(output)
        self._change_state(State.INITIAL)

    def _handle_final(self, char, output):
        assert(False)

def tokenize(string, output=None, path=None):
    t = Tokenizer()
    t.path = path

    output = t.parse_string(string, output)
    t.end(output)

    return output
