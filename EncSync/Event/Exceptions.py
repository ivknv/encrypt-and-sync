#!/usr/bin/env python
# -*- coding: utf-8 -*-

class EventError(Exception):
    def __init__(self, event_name, msg):
        self.event_name = event_name

        Exception.__init__(self, msg)

class UnknownEventError(EventError):
    def __init__(self, event_name):
        EventError.__init__(self, event_name,
                            "Unknown event '{}'".format(event_name))

class DuplicateEventError(EventError):
    def __init__(self, event_name):
        EventError.__init__(self, event_name,
                            "Event '{}' already exists".format(event_name))
