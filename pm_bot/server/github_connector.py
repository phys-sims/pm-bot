"""Compatibility shim for pm_bot.control_plane.github.github_connector."""

import sys as _sys
from pm_bot.control_plane.github import github_connector as _impl

_sys.modules[__name__] = _impl
