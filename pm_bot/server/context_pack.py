"""Compatibility shim for pm_bot.control_plane.context.context_pack."""

import sys as _sys
from pm_bot.control_plane.context import context_pack as _impl

_sys.modules[__name__] = _impl
