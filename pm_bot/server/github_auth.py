"""Compatibility shim for pm_bot.control_plane.github.github_auth."""

import sys as _sys
from pm_bot.control_plane.github import github_auth as _impl

_sys.modules[__name__] = _impl
