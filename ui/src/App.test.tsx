import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "./App";

vi.stubGlobal("fetch", vi.fn());

const mockedFetch = vi.mocked(fetch);

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  mockedFetch.mockReset();
  vi.stubGlobal("confirm", vi.fn(() => true));
  mockedFetch.mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes("/repos/search")) {
      return new Response(JSON.stringify({ items: [{ full_name: "phys-sims/pm-bot", already_added: false }], summary: { count: 1 } }), { status: 200 });
    }
    if (url.includes("/repos/add")) {
      return new Response(JSON.stringify({ id: 1, workspace_id: 1, full_name: "phys-sims/pm-bot", default_branch: "main", added_at: "", last_sync_at: "", last_index_at: "", last_error: "" }), { status: 200 });
    }
    if (url.includes("/repos/1/sync")) {
      return new Response(JSON.stringify({ issues_upserted: 2, prs_upserted: 1 }), { status: 200 });
    }
    if (url.includes("/repos/1/status")) {
      return new Response(JSON.stringify({ repo_id: 1, full_name: "phys-sims/pm-bot", last_sync_at: "", last_index_at: "", last_error: "", issues_cached: 2, prs_cached: 1 }), { status: 200 });
    }
    if (url.endsWith("/repos")) {
      return new Response(JSON.stringify({ items: [], summary: { count: 0 } }), { status: 200 });
    }
    if (url.includes("/repos/reindex-docs") || url.includes("/reindex")) {
      return new Response(JSON.stringify({ status: "completed", documents_indexed: 1, chunks_upserted: 1 }), { status: 200 });
    }
    if (url.includes("/inbox")) {
      return new Response(
        JSON.stringify({
          schema_version: "inbox/v1",
          items: [],
          diagnostics: {
            cache: { hit: false, ttl_seconds: 30, key: "x" },
            rate_limit: { remaining: 100, reset_at: "", source: "github" },
            queries: { calls: 0, chunk_size: 5, chunks: [] },
          },
          summary: { count: 0, pm_bot_count: 0, github_count: 0 },
        }),
        { status: 200 },
      );
    }
    if (url.includes("/audit/chain")) {
      return new Response(
        JSON.stringify({
          schema_version: "audit_chain/v1",
          items: [],
          summary: {
            count: 0,
            total: 0,
            next_offset: null,
            filters: { run_id: "", event_type: "", repo: "", actor: "", start_at: "", end_at: "" },
          },
        }),
        { status: 200 },
      );
    }
    if (url.includes("/audit/rollups")) {
      return new Response(
        JSON.stringify({
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
        }),
        { status: 200 },
      );
    }
    return new Response(JSON.stringify({ root: { issue_ref: "", title: "", type: "epic", children: [] }, warnings: [] }), {
      status: 200,
    });
  });
});

test("adds onboarding, repo dashboard, and existing routes to app shell", async () => {
  render(<App />);

  expect(await screen.findByRole("heading", { name: "Unified Inbox" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Onboarding" }));
  expect(await screen.findByRole("heading", { name: "Onboarding Wizard" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Repo Dashboard" }));
  expect(await screen.findByRole("heading", { name: "Repo Dashboard" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Inbox" }));
  expect(await screen.findByRole("heading", { name: "Unified Inbox" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Agent Runs" }));
  expect(await screen.findByRole("heading", { name: "Agent Runs" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Context Pack" }));
  expect(await screen.findByRole("heading", { name: "Context Pack" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Audit Ops" }));
  expect(await screen.findByRole("heading", { name: "Audit Ops" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Plan Intake" }));
  expect(await screen.findByRole("heading", { name: "Plan Intake" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Tree" }));
  expect(await screen.findByRole("heading", { name: "Tree and Dependencies" })).toBeTruthy();
});

test("runs intake-to-proposal flow and approves generated changeset from inbox", async () => {
  const workflowState = {
    proposed: false,
    approved: false,
  };

  mockedFetch.mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.includes("/report-ir/intake")) {
      return new Response(
        JSON.stringify({
          draft_id: "draft-e2e",
          schema_version: "report_ir_draft/v1",
          draft: {
            schema_version: "report_ir/v1",
            report: {
              title: "E2E Plan",
              generated_at: "2026-02-27",
              scope: { org: "phys-sims", repos: ["phys-sims/pm-bot"] },
            },
            epics: [{ stable_id: "epic:e2e", title: "E2E Epic", area: "triage", priority: "Triage" }],
            features: [
              {
                stable_id: "feat:e2e",
                title: "E2E Feature",
                area: "triage",
                priority: "Triage",
                epic_id: "epic:e2e",
              },
            ],
          },
          validation: { errors: [], warnings: [] },
        }),
        { status: 200 },
      );
    }
    if (url.includes("/report-ir/confirm")) {
      return new Response(
        JSON.stringify({
          status: "confirmed",
          confirmation_id: "confirm-e2e",
          validation: { errors: [], warnings: [] },
          report_ir: { schema_version: "report_ir/v1" },
        }),
        { status: 200 },
      );
    }
    if (url.includes("/report-ir/preview")) {
      return new Response(
        JSON.stringify({
          schema_version: "changeset_preview/v1",
          items: [
            {
              repo: "phys-sims/pm-bot",
              operation: "create_issue",
              item_type: "feature",
              stable_id: "feat:e2e",
              target_ref: "",
              payload: {},
              idempotency_key: "k-e2e",
            },
          ],
          dependency_preview: {
            repos: [
              {
                repo: "phys-sims/pm-bot",
                nodes: [{ stable_id: "feat:e2e", title: "E2E Feature", item_type: "feature", parent_id: "", blocked_by: [], depends_on: [] }],
                edges: [],
              },
            ],
          },
          summary: { count: 1, repos: ["phys-sims/pm-bot"], repo_count: 1 },
        }),
        { status: 200 },
      );
    }
    if (url.includes("/report-ir/propose")) {
      workflowState.proposed = true;
      return new Response(
        JSON.stringify({
          schema_version: "report_ir_proposal/v1",
          items: [
            {
              stable_id: "feat:e2e",
              repo: "phys-sims/pm-bot",
              idempotency_key: "k-e2e",
              changeset: {
                id: 77,
                operation: "create_issue",
                repo: "phys-sims/pm-bot",
                payload: {},
                status: "proposed",
                requested_by: "ui-operator",
                approved_by: "",
                run_id: "run-ui-plan-intake",
                target_ref: "",
                idempotency_key: "k-e2e",
                reason_code: "pending_approval",
                created_at: "2026-02-27T00:00:00Z",
                updated_at: "2026-02-27T00:00:00Z",
              },
            },
          ],
          summary: { count: 1 },
        }),
        { status: 200 },
      );
    }
    if (url.includes("/inbox")) {
      const hasPendingApproval = workflowState.proposed && !workflowState.approved;
      return new Response(
        JSON.stringify({
          schema_version: "inbox/v1",
          items: hasPendingApproval
            ? [
                {
                  source: "pm_bot",
                  item_type: "approval",
                  id: "changeset:77",
                  title: "Approve create_issue",
                  repo: "phys-sims/pm-bot",
                  url: "",
                  state: "pending",
                  priority: "",
                  age_hours: 0,
                  action: "approve",
                  requires_internal_approval: true,
                  stale: false,
                  stale_reason: "",
                  metadata: { changeset_id: 77 },
                },
              ]
            : [],
          diagnostics: {
            cache: { hit: false, ttl_seconds: 30, key: "inbox" },
            rate_limit: { remaining: 100, reset_at: "", source: "github" },
            queries: { calls: 0, chunk_size: 5, chunks: [] },
          },
          summary: {
            count: hasPendingApproval ? 1 : 0,
            pm_bot_count: hasPendingApproval ? 1 : 0,
            github_count: 0,
          },
        }),
        { status: 200 },
      );
    }
    if (url.includes("/changesets/77/approve") && init?.method === "POST") {
      workflowState.approved = true;
      return new Response(JSON.stringify({ status: "applied" }), { status: 200 });
    }
    if (url.includes("/audit/chain")) {
      return new Response(
        JSON.stringify({
          schema_version: "audit_chain/v1",
          items: [],
          summary: {
            count: 0,
            total: 0,
            next_offset: null,
            filters: { run_id: "", event_type: "", repo: "", actor: "", start_at: "", end_at: "" },
          },
        }),
        { status: 200 },
      );
    }
    if (url.includes("/audit/rollups")) {
      return new Response(
        JSON.stringify({
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
        }),
        { status: 200 },
      );
    }
    return new Response(JSON.stringify({ root: { issue_ref: "", title: "", type: "epic", children: [] }, warnings: [] }), {
      status: 200,
    });
  });

  render(<App />);

  await userEvent.click(screen.getByRole("button", { name: "Plan Intake" }));
  expect(await screen.findByRole("heading", { name: "Plan Intake" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: /Draft from intake/ }));
  await userEvent.click(screen.getByRole("button", { name: /Confirm report_ir/ }));
  await userEvent.click(screen.getByRole("button", { name: /Preview operations/ }));
  await userEvent.click(screen.getByRole("button", { name: /Propose changesets/ }));

  expect(await screen.findByText(/Created changesets: 1/)).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Inbox" }));
  expect(await screen.findByRole("heading", { name: "Unified Inbox" })).toBeTruthy();
  expect(await screen.findByText(/Total: 1/)).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Approve" }));
  expect(await screen.findByText(/Total: 0/)).toBeTruthy();
  expect(await screen.findByText("No inbox items.")).toBeTruthy();
});
