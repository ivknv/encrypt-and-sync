# -*- coding: utf-8 -*-

__version__ = "0.6.4"

import eventlet

eventlet.monkey_patch(socket=True, time=True, select=True)
