#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["Prompter", "LoopedPrompter"]

class Prompter(object):
    def __init__(self, message=""):
        self.response = None
        self.message = message

    def preinput(self):
        pass

    def input(self):
        self.response = input(self.message)

    def postinput(self):
        pass

    def prompt(self):
        self.preinput()
        self.input()
        self.postinput()

        return self.response

    def __call__(self):
        return self.prompt()

class LoopedPrompter(Prompter):
    def __init__(self, message=""):
        Prompter.__init__(self, message)

        self.quit = False

    def prompt(self):
        while not self.quit:
            Prompter.prompt(self)

        return self.response
