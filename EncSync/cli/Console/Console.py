#!/usr/bin/env python
# -*- coding: utf-8 -*-

use_readline = False

try:
    import readline
    use_readline = True
except ImportError:
    try:
        import pyreadline as readline
        use_readline = True
    except ImportError:
        pass

import subprocess
import shlex

from ...EncScript import Parser, Tokenizer, ast2program
from .. import common
from ..common import show_error
from ..Environment import Environment
from .ConsoleProgram import ConsoleProgram

class Console(object):
    def __init__(self, encsync):
        self.cwd = "/"
        self.pwd = "/"
        self.env = Environment()
        self.exit_code = 0
        self.quit = False
        self.encsync = encsync

    def execute_commands(self, ast):
        program = ConsoleProgram([])

        try:
            ast2program(ast, program)
        except ValueError as e:
            show_error("Error: %s" % e)
            return 1

        try:
            ret = program.evaluate(self)
        except KeyboardInterrupt:
            ret = 130
        except SystemExit as e:
            ret = e.code

        return ret

    def execute(self, s):
        parser = Parser()
        tokenizer = Tokenizer()

        parser.tokens = tokenizer.parse_string(s)
        tokenizer.end(parser.tokens)

        ast = parser.parse()

        self.exit_code = self.execute_commands(ast)

        return self.exit_code

    def input_loop(self):
        parser = Parser()
        tokenizer = Tokenizer()

        prompt_more = False

        output = []

        while not self.quit:
            try:
                if prompt_more:
                    msg = "...> "
                    prompt_more = False
                else:
                    self.exit_code = 0
                    msg = "{}\nEncSync console> ".format(self.cwd)

                line = input(msg)

                try:
                    for i in line:
                        tokenizer.next_char(i, output)

                    if not tokenizer.in_quotes and not tokenizer.escape:
                        tokenizer.end(output)

                        parser.tokens = output
                        ast = parser.parse()

                        self.exit_code = self.execute_commands(ast)

                        output = []

                        tokenizer.reset()
                        parser.reset()
                    else:
                        prompt_more = True
                        tokenizer.next_char("\n", output)
                except ValueError as e:
                    show_error("Error: %s" % e)
                    self.exit_code = 1
                    tokenizer.reset()
                    parser.reset()
                    output = []
            except KeyboardInterrupt:
                output = []
                parser.reset()
                print("")
            except EOFError:
                break

        return self.exit_code

def run_console(env):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    if use_readline:
        readline.parse_and_bind("tab: complete")

    console = Console(encsync)
    console.env.parent = env

    return console.input_loop()
