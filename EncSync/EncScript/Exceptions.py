#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["EncScriptError", "TokenizerError", "ParserError",
           "UnexpectedCharacterError"]

class EncScriptError(BaseException):
    pass

class TokenizerError(EncScriptError):
    pass

class UnexpectedCharacterError(TokenizerError):
    def __init__(self, path, line_num, char_num, msg=""):
        if path is None:
            location = "%d:%d" % (line_num, char_num)
        else:
            location = "%s:%d:%d" % (path, line_num, char_num)

        msg = "Error at %s: %s" % (location, msg)
        TokenizerError.__init__(self, msg)

        self.path = path
        self.line_num, self.char_num = line_num, char_num

class ParserError(EncScriptError):
    pass

class UnexpectedTokenError(ParserError):
    def __init__(self, path, line_num, char_num, msg=""):
        if path is None:
            location = "%d:%d" % (line_num, char_num)
        else:
            location = "%s:%d:%d" % (path, line_num, char_num)

        msg = "Error at %s: %s" % (location, msg)

        ParserError.__init__(self, msg)

        self.path = path
        self.line_num, self.char_num = line_num, char_num
