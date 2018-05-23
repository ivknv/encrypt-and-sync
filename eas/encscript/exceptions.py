# -*- coding: utf-8 -*-

__all__ = ["EncScriptError", "TokenizerError", "ParserError", "UnexpectedCharacterError",
           "ASTConversionError", "UnknownCommandError", "NotACommandError",
           "UnknownBlockError", "NotABlockError", "EvaluationError"]

class EncScriptError(Exception):
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

class ASTConversionError(EncScriptError):
    def __init__(self, ast, msg=""):
        EncScriptError.__init__(self, msg)
        self.ast = ast

class UnknownCommandError(ASTConversionError):
    pass

class NotACommandError(ASTConversionError):
    pass

class UnknownBlockError(ASTConversionError):
    pass

class NotABlockError(ASTConversionError):
    pass

class EvaluationError(EncScriptError):
    def __init__(self, node, msg=""):
        EncScriptError.__init__(self, msg)
        self.node = node
