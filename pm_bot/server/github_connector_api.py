"""Compatibility shim for pm_bot.control_plane.github.github_connector_api."""

import sys as _sys
from pm_bot.control_plane.github import github_connector_api as _impl

_sys.modules[__name__] = _impl
