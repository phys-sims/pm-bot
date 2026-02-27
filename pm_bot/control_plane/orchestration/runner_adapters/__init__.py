"""Runner adapter registration and environment-driven selection."""

from __future__ import annotations

import os
from typing import Any

from pm_bot.control_plane.orchestration.runner_adapters.manual import ManualRunnerAdapter
from pm_bot.control_plane.orchestration.runner_adapters.provider_stub import (
    ProviderStubRunnerAdapter,
)


def registered_runner_adapters(
    enable_provider_stub: bool = False,
    *,
    db: Any | None = None,
) -> dict[str, Any]:
    adapters: dict[str, Any] = {ManualRunnerAdapter.name: ManualRunnerAdapter()}
    if db is not None:
        import importlib

        adapter_module = importlib.import_module("pm_bot.execution_plane.langgraph.adapter")
        checkpointer_module = importlib.import_module(
            "pm_bot.execution_plane.langgraph.checkpointer"
        )
        checkpointer = checkpointer_module.FsDbCheckpointer(metadata_store=db)
        langgraph = adapter_module.LangGraphRunnerAdapter(
            audit_sink=db,
            interrupt_store=db,
            run_store=db,
            artifact_store=db,
            checkpointer=checkpointer,
        )
        adapters[langgraph.name] = langgraph
    if enable_provider_stub:
        adapters[ProviderStubRunnerAdapter.name] = ProviderStubRunnerAdapter()
    return dict(sorted(adapters.items(), key=lambda kv: kv[0]))


def build_runner_adapters_from_env(
    env: dict[str, str] | None = None,
    *,
    db: Any | None = None,
) -> dict[str, Any]:
    env_map = env or os.environ
    enable_provider = str(env_map.get("PM_BOT_RUNNER_ENABLE_PROVIDER_STUB", "")).strip().lower()
    enabled = enable_provider in {"1", "true", "yes", "on"}
    return registered_runner_adapters(enable_provider_stub=enabled, db=db)


def default_runner_adapter_name(
    env: dict[str, str] | None = None,
    *,
    adapters: dict[str, Any] | None = None,
) -> str:
    env_map = env or os.environ
    available = adapters or build_runner_adapters_from_env(env_map)
    configured = str(env_map.get("PM_BOT_RUNNER_DEFAULT_ADAPTER", "")).strip()
    if configured and configured in available:
        return configured
    return ManualRunnerAdapter.name
