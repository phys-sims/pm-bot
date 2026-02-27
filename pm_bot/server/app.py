"""Compatibility shim for pm_bot.control_plane.api.app."""

import sys as _sys
from pm_bot.control_plane.api import app as _impl

_sys.modules[__name__] = _impl

if __name__ == "__main__":
    raise SystemExit(_impl.main())
