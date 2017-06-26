#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

class Token(object):
    UNDEFINED  = 0
    SIMPLEWORD = 1
    WORD       = 2
    LCBR       = 3
    RCBR       = 4
    SEP        = 5
    END        = 6

    def __init__(self, string, token_type=None):
        if token_type is None:
            token_type = Token.UNDEFINED
        self.string = string
        self.type = token_type

    def __repr__(self):
        types = {Token.UNDEFINED:  "UNDEFINED",
                 Token.SIMPLEWORD: "SIMPLEWORD",
                 Token.WORD:       "WORD",
                 Token.LCBR:       "LCBR",
                 Token.RCBR:       "RCBR",
                 Token.SEP:        "SEP",
                 Token.END:        "END"}

        typestr = types.get(self.type, self.type)

        if self.string:
            return "<Token string=%r type=%s>" % (self.string, typestr)

        return "<Token type=%s>" % (typestr)

class Char(object):
    R_SIMPLE = re.compile(r"^[A-Za-z0-9_-]$")
    escape_map = {"n":  "\n",
                  "r":  "\r",
                  "t":  "\t",
                  "\n": ""}

    def __init__(self, char):
        self._char = char
        self.escaped = False

    @property
    def char(self):
        if not self.escaped:
            return self._char

        return self.escape_map.get(self._char, self._char)

    @char.setter
    def char(self, value):
        self._char = value

    def is_whitespace(self):
        if self.escaped:
            return self.char in ("\r",)
        return self.char in (" ", "\r", "\n", "\t")

    def is_newline(self):
        return not self.escaped and self.char == "\n"

    def is_separator(self):
        return not self.escaped and self.char in (";", "\n")

    def is_quotes(self):
        return not self.escaped and self.char in ("'", '"')

    def is_escape(self):
        return not self.escaped and self.char == "\\"

    def is_simple(self):
        return not self.escaped and Char.R_SIMPLE.match(self.char) is not None

    def is_lcbr(self):
        return not self.escaped and self.char == "{"

    def is_rcbr(self):
        return not self.escaped and self.char == "}"

    def is_comment(self):
        return not self.escaped and self.char == "#"

    def __repr__(self):
        if self.escaped:
            if self._char == "'":
                return '"\\%s"' % self._char
            return "'\\%s'" % self._char

        return repr(self._char)

class Tokenizer(object):
    STATE_INITIAL    = 0
    STATE_SIMPLEWORD = 1
    STATE_WORD       = 2
    STATE_COMMENT    = 3
    STATE_FINAL      = 4

    def __init__(self):
        self.state = Tokenizer.STATE_INITIAL
        self.cur_token = Token("")
        self.escape = False
        self.in_quotes = False
        self.quote_char = None

        self._state_handlers = {Tokenizer.STATE_INITIAL:    self._handle_initial,
                                Tokenizer.STATE_SIMPLEWORD: self._handle_simpleword,
                                Tokenizer.STATE_WORD:       self._handle_word,
                                Tokenizer.STATE_COMMENT:    self._handle_comment}

    def _change_state(self, new_state):
        self.state = new_state

    def _enter_quotes(self, quote_char):
        self.in_quotes = True
        self.quote_char = quote_char

    def _exit_quotes(self):
        self.in_quotes = False
        self.quote_char = None

    def _push_token(self, output):
        if self.cur_token.type != Token.UNDEFINED:
            output.append(self.cur_token)
        self.cur_token = Token("")

    def end(self, output):
        self._push_token(output)

        self.cur_token.type = Token.END
        self._push_token(output)

        self._change_state(Tokenizer.STATE_FINAL)

    def reset(self):
        self.escape = False
        self._exit_quotes()
        self._change_state(Tokenizer.STATE_INITIAL)
        self.cur_token = Token("")

    def parse_string(self, string, output=None):
        if output is None:
            output = []

        for c in string:
            self.next_char(c, output)

        return output

    def next_char(self, char, output):
        if isinstance(char, str):
            char = Char(char)

        if self.escape:
            char.escaped = True
            self.escape = False

        if char.is_escape():
            self.escape = True
            return

        if self.in_quotes:
            if char.is_quotes() and char.char == self.quote_char:
                self._exit_quotes()
            else:
                self.cur_token.type = Token.WORD
                self.cur_token.string += char.char

            return
        elif char.is_quotes() and self.state != Tokenizer.STATE_COMMENT:
            if self.state == Tokenizer.STATE_INITIAL:
                self.state = Tokenizer.STATE_WORD

            self._enter_quotes(char.char)
            return
        elif char.is_comment() and self.state != Tokenizer.STATE_COMMENT:
            self._push_token(output)
            self._change_state(Tokenizer.STATE_COMMENT)
            return

        self._state_handlers[self.state](char, output)

    def _handle_initial(self, char, output):
        if char.is_whitespace():
            return

        if char.is_separator():
            self.cur_token.type = Token.SEP
            self.cur_token.string += char.char

            self._push_token(output)
        elif char.is_lcbr():
            self.cur_token.type = Token.LCBR
            self.cur_token.string = char.char

            self._push_token(output)
        elif char.is_rcbr():
            self.cur_token.type = Token.RCBR
            self.cur_token.string = char.char

            self._push_token(output)
        else:
            if char.is_simple():
                self.cur_token.type = Token.SIMPLEWORD
                self._change_state(Tokenizer.STATE_SIMPLEWORD)
            else:
                self.cur_token.type = Token.WORD
                self._change_state(Tokenizer.STATE_WORD)

            self.cur_token.string += char.char

    def _handle_word(self, char, output):
        if char.is_separator():
            self._push_token(output)

            self.cur_token.type = Token.SEP
            self.cur_token.string += char.char

            self._push_token(output)

            self._change_state(Tokenizer.STATE_INITIAL)
        elif char.is_whitespace():
            self._push_token(output)
        elif char.is_lcbr():
            self._push_token(output)

            self.cur_token.type = Token.LCBR
            self.cur_token.string = char.char

            self._push_token(output)

            self._change_state(Tokenizer.STATE_INITIAL)
        elif char.is_rcbr():
            self._push_token(output)

            self.cur_token.type = Token.RCBR
            self.cur_token.string = char.char

            self._push_token(output)

            self._change_state(Tokenizer.STATE_INITIAL)
        else:
            self.cur_token.type = Token.WORD
            self.cur_token.string += char.char

    def _handle_simpleword(self, char, output):
        if char.is_separator():
            self._push_token(output)

            self.cur_token.type = Token.SEP
            self.cur_token.string += char.char

            self._push_token(output)

            self._change_state(Tokenizer.STATE_INITIAL)
        elif char.is_whitespace():
            self._push_token(output)
        elif char.is_lcbr():
            self._push_token(output)

            self.cur_token.type = Token.LCBR
            self.cur_token.string = char.char

            self._push_token(output)

            self._change_state(Tokenizer.STATE_INITIAL)
        elif char.is_rcbr():
            self._push_token(output)

            self.cur_token.type = Token.RCBR
            self.cur_token.string = char.char

            self._push_token(output)

            self._change_state(Tokenizer.STATE_INITIAL)
        else:
            self.cur_token.string += char.char

            if char.is_simple():
                self.cur_token.type = Token.SIMPLEWORD
            else:
                self.cur_token.type = Token.WORD
                self._change_state(Tokenizer.STATE_WORD)

    def _handle_comment(self, char, output):
        if char.is_newline():
            self._change_state(Tokenizer.STATE_INITIAL)
