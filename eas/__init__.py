# -*- coding: utf-8 -*-

__version__ = "0.7.0"

import eventlet

eventlet.monkey_patch(socket=True, time=True, select=True)
