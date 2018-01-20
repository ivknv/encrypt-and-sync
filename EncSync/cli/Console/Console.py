#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import traceback

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

from ...EncScript import Parser, Tokenizer, ast2program
from ...EncScript.Exceptions import EncScriptError
from ...EncryptedStorage import EncryptedStorage
from ... import Paths
from .. import common
from ..common import show_error
from ..Environment import Environment
from .ConsoleProgram import ConsoleProgram

class Console(object):
    def __init__(self, encsync, env):
        self.storages = {}
        self.cwd = Paths.from_sys(os.getcwd())
        self.pwd = self.cwd
        self.env = env
        self.exit_code = 0
        self.quit = False
        self.encsync = encsync
        self.cur_storage = self.get_storage("local")
        self.previous_storage = self.cur_storage

    def change_storage(self, name, new_path=None):
        if name == self.cur_storage.name:
            return

        new_storage = self.get_storage(name)

        self.cur_storage, self.previous_storage = new_storage, self.cur_storage

        if new_path is None:
            if name == "local":
                new_path = Paths.from_sys(os.getcwd())
            else:
                new_path = "/"

        self.cwd, self.pwd = new_path, self.cwd

    def get_storage(self, name):
        try:
            return self.storages[name]
        except KeyError:
            directory = self.env["db_dir"]
            storage = EncryptedStorage(self.encsync, name, directory)
            self.storages[name] = storage
            return storage

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
                    msg = "%s://%s\nConsole> " % (self.cur_storage.name, self.cwd,)

                line = input(msg)

                try:
                    for i in line:
                        tokenizer.next_char(i, output)

                    if not tokenizer.in_quotes and not tokenizer.escape:
                        tokenizer.next_char("\n", output)
                        tokenizer.end(output)

                        parser.tokens = output
                        ast = parser.parse()

                        self.exit_code = self.execute_commands(ast)

                        output = []

                        tokenizer.reset_state()
                        parser.reset_state()
                    else:
                        prompt_more = True

                        tokenizer.next_char("\n", output)
                except (KeyboardInterrupt, EOFError) as e:
                    raise e
                except Exception as e:
                    if isinstance(e, EncScriptError):
                        show_error("EncScriptError: %s" % (e,))
                    else:
                        traceback.print_exc()
                    self.exit_code = 1

                    tokenizer.line_num += 1

                    tokenizer.reset_state()
                    parser.reset_state()
                    output = []
            except KeyboardInterrupt:
                output = []
                parser.reset_state()
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

    console = Console(encsync, Environment(env))
    console.env.parent = env

    return console.input_loop()
