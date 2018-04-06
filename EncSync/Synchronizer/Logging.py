#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from ..Event.Receiver import Receiver

__all__ = ["logger", "fail_logger", "TaskFailLogReceiver", "TargetFailLogReceiver"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

fail_logger = logging.getLogger("synchronizer-fails")
fail_logger.setLevel(logging.DEBUG)

class TaskFailLogReceiver(Receiver):
    def on_status_changed(self, event, *args, **kwargs):
        task = event.emitter
        target = task.parent

        if task.status != "failed":
            return

        task_types = {("new", "f"): "file upload",
                      ("new", "d"): "directory creation",
                      ("rm", "f"): "file removal",
                      ("rm", "d"): "directory removal",
                      ("update", "f"): "file update"}

        assert(not (task.type == "update" and task.type == "d"))

        fail_logger.info("[%s -> %s][%s]: %s task failed" % (target.folder1["name"],
                                                             target.folder2["name"],
                                                             task.path,
                                                             task_types[(task.type, task.node_type)]))

class TargetFailLogReceiver(Receiver):
    def on_status_changed(self, event, *args, **kwargs):
        target = event.emitter

        if target.status != "failed":
            return

        fail_logger.info("[%s -> %s]: synchronization failed" % (target.folder1["name"],
                                                                 target.folder2["name"]))
