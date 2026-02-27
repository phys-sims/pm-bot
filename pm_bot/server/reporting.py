"""Compatibility shim for pm_bot.control_plane.orchestration.reporting."""

import sys as _sys
from pm_bot.control_plane.orchestration import reporting as _impl

_sys.modules[__name__] = _impl
