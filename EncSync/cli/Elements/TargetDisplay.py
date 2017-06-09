#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import RootElement, TargetList, WorkerList, TargetManagerInfo

class TargetDisplay(RootElement):
    def __init__(self, target_manager=None):
        RootElement.__init__(self)

        self.quit = self.force_quit = False
        self.targets = []
        self.target_list = TargetList(target_manager, self.targets, self)
        self.worker_list = WorkerList(target_manager, self)
        self.manager_info = TargetManagerInfo(target_manager)

        self.target_manager = target_manager

        self.add_key_handler((ord("q"), ord("Q")), self.handle_quit)
        self.add_key_handler((ord("\t"),), self.handle_tab)

        self.elements = [self.manager_info,
                         self.target_list,
                         self.worker_list]

    def handle_quit(self, k):
        if k == ord("q"):
            self.quit = True
            self.target_manager.stop()

            for target in self.targets:
                target.change_status("suspended")

        elif k == ord("Q"):
            self.quit = True
            self.force_quit = True

    def handle_tab(self, k):
        if self.target_list.focused:
            self.worker_list.focus()
        else:
            self.target_list.focus()

    @property
    def highlight_pair(self):
        assert(self.target_list.highlight_pair == self.worker_list.highlight_pair)

        return self.target_list.highlight_pair

    @highlight_pair.setter
    def highlight_pair(self, value):
        self.target_list.highlight_pair = value
        self.worker_list.highlight_pair = value

    @property
    def manager_name(self):
        return self.manager_info.manager_name

    @manager_name.setter
    def manager_name(self, value):
        self.manager_info.manager_name = value

    def stop_condition(self):
        return (self.quit and not self.target_manager.is_alive()) or self.force_quit

    def getch_stop_condition(self):
        return self.stop_condition()

    def getch_loop(self, window):
        try:
            RootElement.getch_loop(self, window)
        finally:
            self.quit = True
            self.force_quit = True
