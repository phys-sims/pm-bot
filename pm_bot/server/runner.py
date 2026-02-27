"""Compatibility shim for pm_bot.control_plane.orchestration.runner."""

import sys as _sys
from pm_bot.control_plane.orchestration import runner as _impl

_sys.modules[__name__] = _impl
