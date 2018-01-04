#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

__all__ = ["logger"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
