#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import readline
import subprocess
import shlex

from .parser import Parser
from ... import paths
from .. import common
from .commands import cmd_cd, cmd_ls, cmd_cat, cmd_exit, cmd_echo

global_vars = common.global_vars

class Console(object):
    def __init__(self, encsync):
        self.cwd = "/"
        self.pwd = "/"
        self.quit = False
        self.commands = {"ls": cmd_ls,
                         "cd": cmd_cd,
                         "cat": cmd_cat,
                         "exit": cmd_exit,
                         "echo": cmd_echo}
        self.encsync = encsync

    def execute_command(self, command):
        if command.is_shell:
            subprocess.call(shlex.split(command[0]))
            return

        try:
            func = self.commands[command[0]]
        except KeyError:
            print("Error: unknown command %r" % command[0], file=sys.stderr)
            return

        try:
            func(self, command)
        except SystemExit:
            pass

    def input_loop(self):
        parser = Parser()

        cur_line = ""
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
                    parser.next_char(i, output)

                if not parser.in_quotes and not parser.escape:
                    parser.finalize(output)

                    for cmd in output:
                        if self.quit:
                            break
                        self.execute_command(cmd)
                    output = []

                    parser.reset()
                else:
                    prompt_more = True
                    parser.next_char("\n", output)
            except KeyboardInterrupt:
                output = []
                parser.reset()
                print("")
            except EOFError:
                break

def run_console():
    encsync = common.make_encsync()

    readline.parse_and_bind("tab: complete")
    console = Console(encsync)
    console.input_loop()
