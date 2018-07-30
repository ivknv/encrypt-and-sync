# -*- coding: utf-8 -*-

__version__ = "0.7.2"

import os
import sys

if sys.platform.startswith("win") and os.environ.get("EAS_USE_EVENTLET", "1") != "0":
    try:
        import eventlet

        # Workaround for https://bugs.python.org/issue33838 
        eventlet.monkey_patch(socket=True)
    except ImportError:
        pass
