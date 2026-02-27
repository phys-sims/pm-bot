"""Compatibility shim for pm_bot.control_plane.orchestration.runner_adapters.manual."""

import sys as _sys
from pm_bot.control_plane.orchestration.runner_adapters import manual as _impl

_sys.modules[__name__] = _impl
