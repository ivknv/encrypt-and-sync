#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Emitter import Emitter
from .Receiver import Receiver

class EventHandler(Emitter, Receiver):
    def __init__(self):
        Emitter.__init__(self)
        Receiver.__init__(self)
