#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from ..events import Receiver

__all__ = ["logger", "fail_logger", "TaskFailLogReceiver", "TargetFailLogReceiver",
           "WorkerFailLogReceiver", "SynchronizerFailLogReceiver"]

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
                      ("update", "f"): "file update",
                      ("modified", "f"): "setting modified date",
                      ("modified", "d"): "setting modified date",
                      ("chmod", "f"): "setting file mode",
                      ("chmod", "d"): "setting file mode",
                      ("chown", "f"): "setting file ownership",
                      ("chown", "d"): "setting file ownership"}

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

class WorkerFailLogReceiver(Receiver):
    def on_error(self, event, exc, *args, **kwargs):
        worker = event.emitter
        task = worker.cur_task

        if task is None:
            return

        target = task.parent

        if exc.__class__.__module__ is not None:
            exc_name = exc.__class__.__module__ + "." + exc.__class__.__qualname__
        else:
            exc_name = exc.__class__.__qualname__

        fail_logger.info("[%s -> %s][%s]: error: %s: %s" % (target.folder1["name"],
                                                            target.folder2["name"],
                                                            task.path,
                                                            exc_name, exc))

class SynchronizerFailLogReceiver(Receiver):
    def on_error(self, event, exc, *args, **kwargs):
        synchronizer = event.emitter
        target = synchronizer.cur_target

        if target is None:
            return

        if exc.__class__.__module__ is not None:
            exc_name = exc.__class__.__module__ + "." + exc.__class__.__qualname__
        else:
            exc_name = exc.__class__.__qualname__

        fail_logger.info("[%s -> %s]: error: %s: %s" % (target.folder1["name"],
                                                        target.folder2["name"],
                                                        exc_name, exc))
