"""Compatibility shim for pm_bot.execution_plane.langgraph.tools.llm.providers.openai."""

import sys as _sys
from pm_bot.execution_plane.langgraph.tools.llm.providers import openai as _impl

_sys.modules[__name__] = _impl
