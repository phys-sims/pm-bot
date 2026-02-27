"""Compatibility shim for pm_bot.execution_plane.langgraph.tools.llm.capabilities."""

import sys as _sys
from pm_bot.execution_plane.langgraph.tools.llm import capabilities as _impl

_sys.modules[__name__] = _impl
