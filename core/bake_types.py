"""Shared immutable data contracts for BakeNexus execution modules."""

from collections import namedtuple


BakeStep = namedtuple("BakeStep", ["job", "task", "channels", "frame_info"])
BakeTask = namedtuple(
    "BakeTask", ["objects", "materials", "active_obj", "base_name", "folder_name"]
)
