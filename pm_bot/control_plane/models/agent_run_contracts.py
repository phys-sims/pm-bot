"""Pydantic contracts for agent run v2, interrupts, and artifacts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RunBudgetV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_total_tokens: int = Field(ge=1)
    max_tool_calls: int = Field(ge=1)
    max_wall_seconds: int = Field(ge=1)
    max_retrieval_tokens: int | None = Field(default=None, ge=1)


class RunScopesV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo: str = Field(min_length=3)


class AgentRunExecutionV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: Literal["langgraph"]
    graph_id: str = Field(min_length=1)
    thread_id: str | None = None
    budget: RunBudgetV1
    tools_allowed: list[str] = Field(min_length=1)
    scopes: RunScopesV1


class AgentRunSpecV2(BaseModel):
    """Agent run contract for langgraph-backed execution."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["agent_run_spec/v2"] = "agent_run_spec/v2"
    run_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    inputs: dict[str, Any] = Field(default_factory=dict)
    execution: AgentRunExecutionV2


class RunInterruptV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["run_interrupt/v1"] = "run_interrupt/v1"
    interrupt_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    risk: Literal["low", "medium", "high"]
    payload: dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "approved", "rejected", "edited"] = "pending"
    decision: dict[str, Any] = Field(default_factory=dict)


class RunArtifactV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["run_artifact/v1"] = "run_artifact/v1"
    artifact_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
