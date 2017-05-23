#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Token(object):
    UNDEFINED    = 0
    WORD         = 1
    SEP          = 2
    SYSCOMMAND   = 3
    ANDOPERATOR  = 4
    END          = 5

    def __init__(self, string, token_type=None):
        if token_type is None:
            token_type = Token.UNDEFINED
        self.string = string
        self.type = token_type

    def __repr__(self):
        types = {Token.UNDEFINED:    "UNDEFINED",
                 Token.WORD:         "WORD",
                 Token.SEP:          "SEP",
                 Token.SYSCOMMAND:   "SYSCOMMAND",
                 Token.ANDOPERATOR:  "ANDOPERATOR",
                 Token.END:          "END"}

        typestr = types.get(self.type, self.type)

        if self.string:
            return "<Token string=%r type=%s>" % (self.string, typestr)

        return "<Token type=%s>" % (typestr)

class Char(object):
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

    def is_separator(self):
        return not self.escaped and self.char in (";", "\n")

    def is_quotes(self):
        return not self.escaped and self.char in ("'", '"')

    def is_escape(self):
        return not self.escaped and self.char == "\\"

    def is_excl(self):
        return not self.escaped and self.char == "!"

    def is_ampersand(self):
        return not self.escaped and self.char == "&"

    def __repr__(self):
        if self.escaped:
            if self._char == "'":
                return '"\\%s"' % self._char
            return "'\\%s'" % self._char

        return repr(self._char)

class Tokenizer(object):
    STATE_INITIAL     = 0
    STATE_WORD        = 1
    STATE_SYSCOMMAND  = 2
    STATE_ANDOPERATOR = 3
    STATE_FINAL       = 4

    def __init__(self):
        self.state = Tokenizer.STATE_INITIAL
        self.cur_token = Token("")
        self.escape = False
        self.in_quotes = False
        self.quote_char = None

        self._state_handlers = {Tokenizer.STATE_INITIAL:     self._handle_initial,
                                Tokenizer.STATE_WORD:        self._handle_word,
                                Tokenizer.STATE_SYSCOMMAND:  self._handle_syscommand,
                                Tokenizer.STATE_ANDOPERATOR: self._handle_andoperator}

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

        if self.state != Tokenizer.STATE_SYSCOMMAND:
            if self.in_quotes:
                if char.is_quotes() and char.char == self.quote_char:
                    self._exit_quotes()
                else:
                    self.cur_token.type = Token.WORD
                    self.cur_token.string += char.char

                return
            elif char.is_quotes():
                if self.state == Tokenizer.STATE_INITIAL:
                    self.state = Tokenizer.STATE_WORD

                self._enter_quotes(char.char)
                return

        self._state_handlers[self.state](char, output)

    def _handle_initial(self, char, output):
        if char.is_whitespace():
            return

        if char.is_separator():
            self._push_token(output)
            self.cur_token.type = Token.SEP
            self.cur_token.string += char.char

            self._push_token(output)
        elif char.is_excl():
            self.cur_token.type = Token.SYSCOMMAND

            self._change_state(Tokenizer.STATE_SYSCOMMAND)
        elif char.is_ampersand():
            self.cur_token.type = Token.ANDOPERATOR
            self.cur_token.string += char.char

            self._change_state(Tokenizer.STATE_ANDOPERATOR)
        else:
            self.cur_token.type = Token.WORD
            self.cur_token.string += char.char

            self._change_state(Tokenizer.STATE_WORD)

    def _handle_word(self, char, output):
        if char.is_separator():
            self._push_token(output)

            self.cur_token.type = Token.SEP
            self.cur_token.string += char.char

            self._push_token(output)

            self._change_state(Tokenizer.STATE_INITIAL)
        elif char.is_whitespace():
            self._push_token(output)
        elif char.is_ampersand():
            self._push_token(output)

            self.cur_token.type = Token.ANDOPERATOR
            self.cur_token.string += char.char

            self._change_state(Tokenizer.STATE_ANDOPERATOR)
        else:
            self.cur_token.type = Token.WORD
            self.cur_token.string += char.char

    def _handle_syscommand(self, char, output):
        if char.char == "\n" and not char.char.escaped:
            self._push_token(output)

            self._change_state(Tokenizer.STATE_INITIAL)
            return

        self.cur_token.string += char.char

    def _handle_andoperator(self, char, output):
        if char.is_ampersand():
            self.cur_token.string += char.char

            self._push_token(output)

            self._change_state(Tokenizer.STATE_INITIAL)
        else:
            raise ValueError("Unexpected character: %r" % char)
