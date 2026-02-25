import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { AuditOpsPage } from "./AuditOpsPage";

vi.stubGlobal("fetch", vi.fn());
const mockedFetch = vi.mocked(fetch);

beforeEach(() => {
  mockedFetch.mockReset();
});

test("loads timeline/rollups and exports incident bundle", async () => {
  mockedFetch
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "audit_chain/v1",
          items: [{ id: 1, event_type: "agent_run_completed", payload: { run_id: "run-1", repo: "phys-sims/pm-bot" }, tenant_context: {}, created_at: "2026-02-25T00:00:00Z" }],
          summary: {
            count: 1,
            total: 1,
            next_offset: null,
            filters: { run_id: "", event_type: "", repo: "", actor: "", start_at: "", end_at: "" },
          },
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "audit_rollups/v1",
          summary: {
            sample_size: 3,
            completion_rate: 0.3333,
            retry_count: 1,
            dead_letter_count: 0,
            denial_count: 1,
            average_queue_age_seconds: 4,
          },
          top_reason_codes: [{ reason_code: "repo_not_allowlisted", count: 1 }],
          repo_concentration: [{ repo: "phys-sims/pm-bot", count: 3 }],
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "audit_chain/v1",
          items: [{ id: 1, event_type: "agent_run_completed", payload: { run_id: "run-1", repo: "phys-sims/pm-bot" }, tenant_context: {}, created_at: "2026-02-25T00:00:00Z" }],
          summary: {
            count: 1,
            total: 1,
            next_offset: null,
            filters: { run_id: "run-1", event_type: "", repo: "", actor: "", start_at: "", end_at: "" },
          },
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "audit_rollups/v1",
          summary: {
            sample_size: 3,
            completion_rate: 0.3333,
            retry_count: 1,
            dead_letter_count: 0,
            denial_count: 1,
            average_queue_age_seconds: 4,
          },
          top_reason_codes: [{ reason_code: "repo_not_allowlisted", count: 1 }],
          repo_concentration: [{ repo: "phys-sims/pm-bot", count: 3 }],
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "incident_bundle/v1",
          export: { run_id: "run-1", actor: "alice", generated_at: "2026-02-25T00:00:00Z" },
          runbook_hooks: {
            retry_storm: "docs/runbooks/first-human-test.md",
            denial_spike: "docs/runbooks/first-human-test.md",
          },
          chain: {
            schema_version: "audit_chain/v1",
            items: [],
            summary: {
              count: 0,
              total: 0,
              next_offset: null,
              filters: { run_id: "", event_type: "", repo: "", actor: "", start_at: "", end_at: "" },
            },
          },
          rollups: {
            schema_version: "audit_rollups/v1",
            summary: {
              sample_size: 0,
              completion_rate: 0,
              retry_count: 0,
              dead_letter_count: 0,
              denial_count: 0,
              average_queue_age_seconds: 0,
            },
            top_reason_codes: [],
            repo_concentration: [],
          },
        }),
        { status: 200 },
      ),
    );

  render(<AuditOpsPage />);

  expect(await screen.findByText(/Loaded 1 timeline event/)).toBeTruthy();
  expect(await screen.findByText(/Sample size: 3/)).toBeTruthy();
  expect(await screen.findByText(/#1 \[agent_run_completed\]/)).toBeTruthy();

  await userEvent.type(screen.getByLabelText("Run ID:"), "run-1");
  await userEvent.type(screen.getByLabelText("Actor:"), "alice");
  await userEvent.click(screen.getByRole("button", { name: "Refresh timeline + rollups" }));
  expect(await screen.findByText(/Loaded 1 timeline event/)).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Export incident bundle" }));
  expect(await screen.findByText(/Exported incident bundle/)).toBeTruthy();
  expect(await screen.findByText(/retry_storm:/)).toBeTruthy();
});
