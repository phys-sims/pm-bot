"""Compatibility shim for pm_bot.execution_plane.langgraph.tools.llm.providers."""

import sys as _sys
from pm_bot.execution_plane.langgraph.tools.llm import providers as _impl

_sys.modules[__name__] = _impl
