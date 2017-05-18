#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import readline
import subprocess
import shlex

from .parser import Parser
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
                         "duplicates": commands.cmd_duplicates}
        self.encsync = encsync

    def execute_command(self, command):
        if command.is_shell:
            try:
                subprocess.call(shlex.split(command[0]))
            except (FileNotFoundError, subprocess.SubprocessError) as e:
                print("Error: %s" %e)

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
