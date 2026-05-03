"""BakeNexus core module.

This module contains the core functionality for texture baking operations,
including image management, node manipulation, UV handling, shading, and
mesh processing.

Submodules:
    - api: Public API functions
    - cage_analyzer: Cage mesh analysis
    - cleanup: Emergency cleanup operations
    - common: Shared utilities and helper functions
    - compat: Blender version compatibility
    - engine: Main baking engine and execution
    - execution: Modal operator execution
    - image_manager: Image creation and management
    - math_utils: Mathematical utilities
    - node_manager: Shader node manipulation
    - shading: Material and shading utilities
    - thumbnail_manager: Preview generation
    - uv_manager: UV layer management
"""

from . import api
from . import cage_analyzer
from . import cleanup
from . import common
from . import compat
from . import engine
from . import execution
from . import image_manager
from . import math_utils
from . import node_manager
from . import shading
from . import thumbnail_manager
from . import uv_manager

__all__ = [
    "api",
    "cage_analyzer",
    "cleanup",
    "common",
    "compat",
    "engine",
    "execution",
    "image_manager",
    "math_utils",
    "node_manager",
    "shading",
    "thumbnail_manager",
    "uv_manager",
]
