#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import OrderedDict
import re

__all__ = ["interpret_choice"]

R_INTERVAL = re.compile(r"^([+-]?\d+:[+-]?\d+)$")
R_INDEX = re.compile(r"^([+-]?\d+)$")

class Word(object):
    INDEX = 0
    INTERVAL = 1
    ALL = 2
    NONE = 3

    def __init__(self, word):
        self.word = word
        self.type = None
        self.negative = False
        self.value = None

    def identify(self):
        word = self.word
        self.negative = is_negative(word)

        if self.negative:
            word = word[1:]

        if is_index(word):
            self.type = Word.INDEX
            self.value = int(word)

            if self.value == 0:
                raise IndexError("Invalid index: 0")
        elif is_interval(word):
            self.type = Word.INTERVAL
            a, b = word.split(":")

            self.value = (int(a), int(b))

            if 0 in self.value:
                raise IndexError("Invalid index: 0")
        elif is_all(word):
            self.type = Word.ALL
            self.value = None
        elif is_none(word):
            self.type = Word.NONE
            self.value = None
        else:
            raise ValueError("Unknown word: %r" % word)

    def interpret(self, values, output):
        func_table = {Word.INDEX:    self._interpret_index,
                      Word.INTERVAL: self._interpret_interval,
                      Word.ALL:      self._interpret_all,
                      Word.NONE:     self._interpret_none}

        func_table[self.type](values, output)

    def _interpret_index(self, values, output):
        if self.value < 0:
            idx = len(values) + self.value + 1
        else:
            idx = self.value

        if idx > len(values) or idx <= 0:
            raise IndexError("Index out of range")

        if self.negative:
            output.pop(idx, None)
        else:
            output[idx] = values[idx - 1]

    def _interpret_interval(self, values, output):
        idx1, idx2 = self.value

        if idx1 < 0:
            idx1 = len(values) + idx1 + 1

        if idx2 < 0:
            idx2 = len(values) + idx2 + 1

        if idx1 > len(values) or idx2 > len(values):
            raise IndexError("Index out of range")

        if idx1 <= 0 or idx2 <= 0:
            raise IndexError("Index out of range")

        for i in range(idx1, idx2 + 1):
            if self.negative:
                output.pop(i, None)
            else:
                output[i] = values[i - 1]

    def _interpret_all(self, values, output):
        if self.negative:
            output.clear()
            return

        for i, value in enumerate(values):
            output[i + 1] = value

    def _interpret_none(self, values, output):
        if self.negative:
            for i, value in enumerate(values):
                output[i + 1] = value
            return

        output.clear()

def interpret_choice(line, values):
    output = OrderedDict()

    for i in line.split():
        word = Word(i)
        word.identify()
        word.interpret(values, output)

    return [i[1] for i in output.items()]

def is_negative(word):
    return word.startswith("!")

def is_interval(word):
    return R_INTERVAL.match(word) is not None

def is_index(word):
    return R_INDEX.match(word) is not None

def is_all(word):
    return word == "all"

def is_none(word):
    return word == "none"
