#!/usr/bin/env python
# -*- coding: utf-8 -*-

import enum

class Token(object):
    class Type(enum.Enum):
        UNDEFINED  = 0
        WORD       = 1
        LCBR       = 2
        RCBR       = 3
        SEP        = 4
        END        = 5

    def __init__(self, string, token_type=Type.UNDEFINED):
        self.string = string
        self.type = token_type

    def __repr__(self):
        if self.string:
            return "<Token string=%r type=%s>" % (self.string, self.type)

        return "<Token type=%s>" % self.type

class Char(object):
    escape_map = {"'":  "'",
                  "\"": "\"",
                  "a":  "\a",
                  "b":  "\b",
                  "e":  "\033",
                  "f":  "\f",
                  "n":  "\n",
                  "r":  "\r",
                  "t":  "\t",
                  "v":  "\v",
                  "\n": ""}

    def __init__(self, char):
        self._char = char
        self.escaped = False
        self.in_quotes = False
        self.c_quote = False
        self.quote_char = None

    @property
    def char(self):
        if not self.escaped:
            return self._char

        if self.in_quotes:
            if self.c_quote:
                return self.escape_map.get(self._char, "\\" + self._char)
            elif self._char != self.quote_char:
                return "\\" + self._char

        return self._char

    @char.setter
    def char(self, value):
        self._char = value

    def is_whitespace(self):
        if self.escaped:
            return self.char in ("\r",)
        return self.char in (" ", "\r", "\n", "\t")

    def is_newline(self):
        return not (self.escaped or self.in_quotes) and self.char == "\n"

    def is_separator(self):
        return not (self.escaped or self.in_quotes) and self.char in (";", "\n")

    def is_quotes(self):
        if self.escaped:
            return False

        if self.in_quotes:
            return self._char == self.quote_char

        return self.char in ("'", '"')

    def is_escape(self):
        if self.in_quotes and self.quote_char == "'" and not self.c_quote:
            return False

        return not self.escaped and self.char == "\\"

    def is_lcbr(self):
        return not (self.escaped or self.in_quotes) and self.char == "{"

    def is_rcbr(self):
        return not (self.escaped or self.in_quotes) and self.char == "}"

    def is_comment(self):
        return not (self.escaped or self.in_quotes) and self.char == "#"

    def is_dollar(self):
        return not (self.escaped or self.in_quotes) and self.char == "$"

    def __repr__(self):
        if self.escaped:
            if self._char == "'":
                return '"\\%s"' % self._char
            return "'\\%s'" % self._char

        return repr(self._char)

class State(enum.Enum):
    INITIAL = 0
    WORD    = 1
    COMMENT = 2
    QUOTES  = 3
    DOLLAR  = 4
    FINAL   = 5

class Tokenizer(object):
    def __init__(self):
        self.state = State.INITIAL
        self.cur_token = Token("")
        self.escape = False
        self.in_quotes = False
        self.c_quote = False
        self.quote_char = None

        self._state_handlers = {State.INITIAL: self._handle_initial,
                                State.WORD:    self._handle_word,
                                State.COMMENT: self._handle_comment,
                                State.QUOTES:  self._handle_quotes,
                                State.DOLLAR:  self._handle_dollar,
                                State.FINAL:   self._handle_final}

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
            output.append(self.cur_token)
        self.cur_token = Token("")

    def end(self, output):
        self._push_token(output)

        self.cur_token.type = Token.Type.END
        self._push_token(output)

        self._change_state(State.FINAL)

    def reset(self):
        self.escape = False
        self._exit_quotes()
        self._change_state(State.INITIAL)
        self.cur_token = Token("")

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

        char.in_quotes = self.in_quotes
        char.quote_char = self.quote_char
        char.c_quote = self.c_quote

        if self.escape:
            char.escaped = True
            self.escape = False

        if char.is_escape():
            self.escape = True
            return

        self._state_handlers[self.state](char, output)

    def _handle_initial(self, char, output):
        if char.is_whitespace():
            return

        if char.is_comment():
            self._change_state(State.COMMENT)
            return

        if char.is_dollar():
            self._change_state(State.DOLLAR)
            self.c_quote = True
            return

        if char.is_quotes():
            self.cur_token.type = Token.Type.SEP

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
        else:
            self.cur_token.type = Token.Type.WORD
            self._change_state(State.WORD)

            self.cur_token.string += char.char

    def _handle_word(self, char, output):
        if char.is_dollar():
            self.c_quote = True
            self._change_state(State.DOLLAR)
            return
        else:
            self.c_quote = False

        if char.is_comment():
            self._push_token(output)
            self._change_state(State.COMMENT)
        elif char.is_quotes():
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

            self.cur_token.type = Token.Type.LCBR
            self.cur_token.string = char.char

            self._push_token(output)
            self._change_state(State.INITIAL)
        elif char.is_rcbr():
            self._push_token(output)

            self.cur_token.type = Token.Type.RCBR
            self.cur_token.string = char.char

            self._push_token(output)
            self._change_state(State.INITIAL)
        else:
            self.cur_token.type = Token.Type.WORD
            self.cur_token.string += char.char

    def _handle_comment(self, char, output):
        if char.is_newline():
            self._change_state(State.INITIAL)

    def _handle_quotes(self, char, output):
        if char.is_quotes() and char.char == self.quote_char:
            self._exit_quotes()
            self._change_state(State.WORD)
        else:
            self.cur_token.type = Token.Type.WORD
            self.cur_token.string += char.char

    def _handle_dollar(self, char, output):
        if not char.is_quotes():
            raise ValueError("Expected quotes")

        self._enter_quotes(char.char)
        self._change_state(State.QUOTES)

    def _handle_final(self, char, output):
        assert(False)
