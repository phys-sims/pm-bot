import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { App } from "./App";

vi.stubGlobal("fetch", vi.fn());

const mockedFetch = vi.mocked(fetch);

beforeEach(() => {
  mockedFetch.mockReset();
  mockedFetch.mockImplementation(async (input) => {
    const url = String(input);
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

test("adds agent-runs, context-pack, and audit routes to app shell", async () => {
  render(<App />);

  expect(await screen.findByRole("heading", { name: "Unified Inbox" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Agent Runs" }));
  expect(await screen.findByRole("heading", { name: "Agent Runs" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Context Pack" }));
  expect(await screen.findByRole("heading", { name: "Context Pack" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Audit Ops" }));
  expect(await screen.findByRole("heading", { name: "Audit Ops" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Tree" }));
  expect(await screen.findByRole("heading", { name: "Tree and Dependencies" })).toBeTruthy();
});
