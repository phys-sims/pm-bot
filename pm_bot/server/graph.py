"""Compatibility shim for pm_bot.control_plane.orchestration.graph."""

import sys as _sys
from pm_bot.control_plane.orchestration import graph as _impl

_sys.modules[__name__] = _impl
