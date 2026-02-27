"""Compatibility shim for pm_bot.control_plane.db.db."""

import sys as _sys
from pm_bot.control_plane.db import db as _impl

_sys.modules[__name__] = _impl
