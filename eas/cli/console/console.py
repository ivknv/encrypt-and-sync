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

from ...encscript import Parser, Tokenizer, ast2program
from ...encscript.exceptions import EncScriptError
from ...encrypted_storage import EncryptedStorage
from ... import pathm
from .. import common
from ..common import show_error
from ..environment import Environment
from ..authenticate_storages import authenticate_storages
from .console_program import ConsoleProgram

__all__ = ["Console", "run_console"]

class Console(object):
    def __init__(self, config, env):
        self.storages = {}
        self.cwd = pathm.from_sys(os.getcwd())
        self.pwd = self.cwd
        self.env = env
        self.exit_code = 0
        self.quit = False
        self.config = config
        self.cur_storage = self.get_storage("local")
        self.previous_storage = self.cur_storage

    def change_storage(self, name, new_path=None):
        if name == self.cur_storage.name:
            return

        new_storage = self.get_storage(name)

        self.cur_storage, self.previous_storage = new_storage, self.cur_storage

        if new_path is None:
            if name == "local":
                new_path = pathm.from_sys(os.getcwd())
            else:
                new_path = "/"

        self.cwd, self.pwd = new_path, self.cwd

    def get_storage(self, name):
        try:
            return self.storages[name]
        except KeyError:
            if name not in self.config.storages:
                ret = authenticate_storages(self.env, (name,))

                if ret:
                    raise ValueError("failed to authenticate storage")

            directory = self.env["db_dir"]
            storage = EncryptedStorage(self.config, name, directory)
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
    config, ret = common.make_config(env)

    if config is None:
        return ret

    if use_readline:
        readline.parse_and_bind("tab: complete")

    console = Console(config, Environment(env))
    console.env.parent = env

    return console.input_loop()
