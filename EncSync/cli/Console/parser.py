#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Character(object):
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
        else:
            return self.char in (" ", "\r", "\n", "\t")

    def is_separator(self):
        return not self.escaped and self.char in (";", "\n")

    def is_quotes(self):
        return not self.escaped and self.char in ("'", '"')

    def is_escape(self):
        return not self.escaped and self.char == "\\"

    def is_excl(self):
        return not self.escaped and self.char == "!"

class Command(list):
    def __init__(self, *args, is_shell=False, **kwargs):
        list.__init__(self, *args, **kwargs)
        self.is_shell = is_shell

class Parser(object):
    STATE_INITIAL = 0
    STATE_COMMAND = 1
    STATE_ARGS    = 2
    STATE_EXCL    = 3

    def __init__(self):
        self.state = self.STATE_INITIAL
        self.cur_word = ""
        self.cur_command = Command()
        self.in_quotes = False
        self.quote_char = None
        self.escape = False

        self.state_handlers = {self.STATE_INITIAL: self.on_STATE_INITIAL,
                               self.STATE_COMMAND: self.on_STATE_COMMAND,
                               self.STATE_ARGS: self.on_STATE_ARGS}

    def reset(self):
        self.state = self.STATE_INITIAL
        self.cur_word = ""
        self.cur_command = Command()
        self.in_quotes = False
        self.quote_char = None
        self.escape = False

    def handle_quotes(self, char):
        if self.in_quotes:
            if char == self.quote_char:
                self.in_quotes = False
                self.quote_char = None
            else:
                self.cur_word += char
        else:
            self.in_quotes = True
            self.quote_char = char

    def append_word(self):
        if self.cur_word:
            self.cur_command.append(self.cur_word)
            self.cur_word = ""

    def append_command(self, output):
        self.append_word()

        if self.cur_command:
            output.append(self.cur_command)
            self.cur_command = Command()

    def next_char(self, char, output):
        if isinstance(char, str):
            char = Character(char)

        char.escaped = self.escape
        self.escape = False

        if char.is_escape():
            self.escape = True
            return

        if self.state == self.STATE_EXCL:
            if char.char == "\n" and not char.escaped:
                self.append_command(output)
            else:
                self.cur_word += char.char
            return

        if self.in_quotes:
            if self.state == self.STATE_INITIAL:
                self.state = self.STATE_COMMAND

            if char.is_quotes():
                self.handle_quotes(char.char)
            else:
                self.cur_word += char.char
            return

        if char.is_quotes():
            self.handle_quotes(char.char)
            return

        self.state_handlers[self.state](char, output)

    def on_STATE_INITIAL(self, char, output):
        if char.is_excl():
            self.state = self.STATE_EXCL
            self.cur_command.is_shell = True

            return

        if char.is_whitespace() or char.is_separator():
            return

        self.state = self.STATE_COMMAND
        self.cur_word += char.char

    def on_STATE_COMMAND(self, char, output):
        if char.is_separator():
            self.append_command(output)
        elif char.is_whitespace():
            self.state = self.STATE_ARGS

            self.append_word()
        else:
            self.cur_word += char.char

    def on_STATE_ARGS(self, char, output):
        if char.is_separator():
            self.state = self.STATE_INITIAL

            self.append_command(output)
        elif char.is_whitespace():
            self.append_word()
        else:
            self.cur_word += char.char

    def finalize(self, output):
        self.append_command(output)

    def parse(self, s, output):
        output = output or []

        for i in s:
            self.next_char(i, output)

        if not self.in_quotes and not self.escape:
            self.finalize(output)
            return True

        return False
