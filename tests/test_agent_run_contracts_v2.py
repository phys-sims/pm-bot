import pytest

from pm_bot.control_plane.models.agent_run_contracts import AgentRunSpecV2


def test_agent_run_spec_v2_validates_langgraph_fields() -> None:
    model = AgentRunSpecV2.model_validate(
        {
            "schema_version": "agent_run_spec/v2",
            "run_id": "run-123",
            "goal": "Create changeset proposal",
            "inputs": {"context_pack_id": "ctx-1"},
            "execution": {
                "engine": "langgraph",
                "graph_id": "repo_change_proposer/v1",
                "thread_id": None,
                "budget": {
                    "max_total_tokens": 1000,
                    "max_tool_calls": 10,
                    "max_wall_seconds": 300,
                },
                "tools_allowed": ["github_read"],
                "scopes": {"repo": "phys-sims/pm-bot"},
            },
        }
    )
    assert model.execution.engine == "langgraph"
    assert model.execution.scopes.repo == "phys-sims/pm-bot"


def test_agent_run_spec_v2_rejects_non_langgraph_engine() -> None:
    with pytest.raises(Exception):
        AgentRunSpecV2.model_validate(
            {
                "schema_version": "agent_run_spec/v2",
                "run_id": "run-123",
                "goal": "Create changeset proposal",
                "inputs": {},
                "execution": {
                    "engine": "other",
                    "graph_id": "repo_change_proposer/v1",
                    "thread_id": None,
                    "budget": {
                        "max_total_tokens": 1000,
                        "max_tool_calls": 10,
                        "max_wall_seconds": 300,
                    },
                    "tools_allowed": ["github_read"],
                    "scopes": {"repo": "phys-sims/pm-bot"},
                },
            }
        )
