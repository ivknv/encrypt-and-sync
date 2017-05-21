#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import readline
import subprocess
import shlex

from .Parser import Parser, AST
from .Tokenizer import Tokenizer
from .. import common
from . import commands

global_vars = common.global_vars

class Console(object):
    def __init__(self, encsync):
        self.cwd = "/"
        self.pwd = "/"
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

        for child in ast.children:
            if child.type == AST.COMMAND:
                self.execute_command(child)
            elif child.type == AST.SYSCOMMAND:
                self.execute_syscommand(child)

    def execute_command(self, ast):
        args = []
        for child in ast.children:
            if child.type == AST.WORD:
                args.append(child.token.string)

        if len(args) == 0:
            return

        try:
            func = self.commands[args[0]]
        except KeyError:
            print("Error: unknown command %r" % args[0], file=sys.stderr)
            return

        try:
            func(self, args)
        except SystemExit:
            pass

    def execute_syscommand(self, ast):
        try:
            subprocess.call(shlex.split(ast.token.string))
        except (FileNotFoundError, subprocess.SubprocessError) as e:
            print("Error: %s" %e, file=sys.stderr)

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
                    msg = "{}\nEncSync console> ".format(self.cwd)

                line = input(msg)

                for i in line:
                    tokenizer.next_char(i, output)

                if not tokenizer.in_quotes and not tokenizer.escape:
                    tokenizer.end(output)

                    parser.tokens = output
                    ast = parser.parse()

                    self.execute_commands(ast)

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

def run_console():
    encsync = common.make_encsync()

    if encsync is None:
        return

    readline.parse_and_bind("tab: complete")
    console = Console(encsync)
    console.input_loop()
