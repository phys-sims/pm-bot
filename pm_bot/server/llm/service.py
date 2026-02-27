"""Compatibility shim for pm_bot.execution_plane.langgraph.tools.llm.service."""

import sys as _sys
from pm_bot.execution_plane.langgraph.tools.llm import service as _impl

_sys.modules[__name__] = _impl
