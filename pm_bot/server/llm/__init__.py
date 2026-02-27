"""Compatibility shim for pm_bot.execution_plane.langgraph.tools.llm."""

import sys as _sys
from pm_bot.execution_plane.langgraph.tools import llm as _impl

_sys.modules[__name__] = _impl
