#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(name)s-Thread-%(thread)d: %(message)s")

handler = logging.FileHandler("scanner.log")
handler.setFormatter(formatter)

logger.addHandler(handler)
