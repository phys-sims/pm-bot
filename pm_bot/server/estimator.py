"""Compatibility shim for pm_bot.control_plane.orchestration.estimator."""

import sys as _sys
from pm_bot.control_plane.orchestration import estimator as _impl

_sys.modules[__name__] = _impl
