"""Compatibility shim for pm_bot.control_plane.artifacts.changesets."""

import sys as _sys
from pm_bot.control_plane.artifacts import changesets as _impl

_sys.modules[__name__] = _impl
