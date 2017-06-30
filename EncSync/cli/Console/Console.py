#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    import readline
except ImportError:
    import pyreadline as readline

import subprocess
import shlex

from .Parser import Parser, AST
from .Tokenizer import Tokenizer
from .. import common
from ..common import show_error
from ..Environment import Environment
from . import commands

class Console(object):
    def __init__(self, encsync):
        self.cwd = "/"
        self.pwd = "/"
        self.env = Environment()
        self.exit_code = 0
        self.quit = False
        self.commands = {"ls":         commands.cmd_ls,
                         "cd":         commands.cmd_cd,
                         "cat":        commands.cmd_cat,
                         "exit":       commands.cmd_exit,
                         "quit":       commands.cmd_exit,
                         "echo":       commands.cmd_echo,
                         "download":   commands.cmd_download,
                         "scan":       commands.cmd_scan,
                         "sync":       commands.cmd_sync,
                         "diffs":      commands.cmd_diffs,
                         "duplicates": commands.cmd_duplicates,
                         "lscan":      commands.cmd_lscan,
                         "rscan":      commands.cmd_rscan}
        self.encsync = encsync

    def execute_commands(self, ast):
        assert(ast.type == AST.PROGRAM)

        ret = 0

        try:
            for child in ast.children:
                if child.type == AST.COMMAND:
                    ret = self.execute_command(child)
                elif child.type == AST.SYSCOMMAND:
                    ret = self.execute_syscommand(child)

                if self.quit:
                    break
        except KeyboardInterrupt:
            ret = 130

        return ret

    def execute_command(self, ast):
        args = []
        for child in ast.children:
            if child.type == AST.WORD:
                args.append(child.token.string)
            elif child.type == AST.ANDOPERATOR:
                ret = self.execute_args(args)

                if ret or self.quit:
                    return ret
                args = []
            elif child.type == AST.COMMAND:
                return self.execute_command(child)
            elif child.type == AST.SYSCOMMAND:
                return self.execute_syscommand(child)

        return self.execute_args(args)

    def execute_args(self, args):
        if len(args) == 0:
            return 0

        try:
            func = self.commands[args[0]]
        except KeyError:
            show_error("Error: unknown command %r" % args[0])
            return 127

        try:
            return func(self, args)
        except SystemExit as e:
            return e.code

    def execute_syscommand(self, ast):
        try:
            return subprocess.call(shlex.split(ast.token.string))
        except FileNotFoundError as e:
            show_error("Error: %s" % e)
            return 127
        except subprocess.SubprocessError as e:
            show_error("Error: %s" % e)
            return 1

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

    readline.parse_and_bind("tab: complete")
    console = Console(encsync)
    console.env.parent = env

    return console.input_loop()
