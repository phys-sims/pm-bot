import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { InboxPage } from "./InboxPage";

vi.stubGlobal("fetch", vi.fn());

const mockedFetch = vi.mocked(fetch);


afterEach(() => {
  cleanup();
});

beforeEach(() => {
  mockedFetch.mockReset();
  vi.stubGlobal("confirm", vi.fn(() => true));
});

test("loads unified inbox and approves pm-bot item", async () => {
  mockedFetch
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "inbox/v1",
          items: [
            {
              source: "pm_bot",
              item_type: "approval",
              id: "changeset:1",
              title: "Approve create_issue",
              repo: "r",
              url: "",
              state: "pending",
              priority: "",
              age_hours: 0,
              action: "approve",
              requires_internal_approval: true,
              stale: false,
              stale_reason: "",
              metadata: { changeset_id: 1 },
            },
            {
              source: "github",
              item_type: "triage",
              id: "github:r#2",
              title: "Review me",
              repo: "r",
              url: "https://github.example/2",
              state: "open",
              priority: "",
              age_hours: 0,
              action: "triage",
              requires_internal_approval: false,
              stale: false,
              stale_reason: "",
              metadata: {},
            },
          ],
          diagnostics: {
            cache: { hit: false, ttl_seconds: 30, key: "x" },
            rate_limit: { remaining: 100, reset_at: "", source: "github" },
            queries: { calls: 1, chunk_size: 5, chunks: [] },
          },
          summary: { count: 2, pm_bot_count: 1, github_count: 1 },
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(new Response(JSON.stringify({ status: "applied" }), { status: 200 }))
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "inbox/v1",
          items: [],
          diagnostics: {
            cache: { hit: true, ttl_seconds: 30, key: "x" },
            rate_limit: { remaining: 100, reset_at: "", source: "github" },
            queries: { calls: 0, chunk_size: 5, chunks: [] },
          },
          summary: { count: 0, pm_bot_count: 0, github_count: 0 },
        }),
        { status: 200 },
      ),
    );

  render(<InboxPage />);

  expect(await screen.findByText(/Total: 2/)).toBeTruthy();
  await userEvent.click(screen.getByRole("button", { name: "Approve changeset" }));

  expect(await screen.findByText(/Total: 0/)).toBeTruthy();
  expect(await screen.findByText("No inbox items.")).toBeTruthy();
  expect(mockedFetch).toHaveBeenCalledTimes(3);
});

test("approves interrupt and resumes run execution", async () => {
  mockedFetch
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "inbox/v1",
          items: [
            {
              source: "pm_bot",
              item_type: "interrupt",
              id: "interrupt:int-1",
              title: "Resolve interrupt",
              repo: "r",
              url: "",
              state: "pending",
              priority: "",
              age_hours: 0,
              action: "resolve",
              requires_internal_approval: true,
              stale: false,
              stale_reason: "",
              metadata: { interrupt_id: "int-1", run_id: "run-1" },
            },
          ],
          diagnostics: {
            cache: { hit: false, ttl_seconds: 30, key: "x" },
            rate_limit: { remaining: 100, reset_at: "", source: "github" },
            queries: { calls: 1, chunk_size: 5, chunks: [] },
          },
          summary: { count: 1, pm_bot_count: 1, github_count: 0 },
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "run_interrupt/v1",
          interrupt_id: "int-1",
          run_id: "run-1",
          thread_id: "thread-1",
          kind: "approval",
          risk: "medium",
          payload: { proposed: true },
          status: "approved",
          decision: { action: "approve", payload: { proposed: true } },
          decision_actor: "ui-user",
          decision_action: "approve",
          created_at: "2026-02-27T00:00:00Z",
          resolved_at: "2026-02-27T00:00:01Z",
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(new Response(JSON.stringify({ run_id: "run-1", status: "running" }), { status: 200 }))
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "inbox/v1",
          items: [],
          diagnostics: {
            cache: { hit: true, ttl_seconds: 30, key: "x" },
            rate_limit: { remaining: 100, reset_at: "", source: "github" },
            queries: { calls: 0, chunk_size: 5, chunks: [] },
          },
          summary: { count: 0, pm_bot_count: 0, github_count: 0 },
        }),
        { status: 200 },
      ),
    );

  render(<InboxPage />);
  await userEvent.click(await screen.findByRole("button", { name: "Approve interrupt" }));
  expect(await screen.findByText("No inbox items.")).toBeTruthy();
});


test("edits interrupt and resumes run execution with edited payload", async () => {
  mockedFetch
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "inbox/v1",
          items: [
            {
              source: "pm_bot",
              item_type: "interrupt",
              id: "interrupt:int-2",
              title: "Resolve interrupt",
              repo: "r",
              url: "",
              state: "pending",
              priority: "",
              age_hours: 0,
              action: "resolve",
              requires_internal_approval: true,
              stale: false,
              stale_reason: "",
              metadata: { interrupt_id: "int-2", run_id: "run-2" },
            },
          ],
          diagnostics: {
            cache: { hit: false, ttl_seconds: 30, key: "x" },
            rate_limit: { remaining: 100, reset_at: "", source: "github" },
            queries: { calls: 1, chunk_size: 5, chunks: [] },
          },
          summary: { count: 1, pm_bot_count: 1, github_count: 0 },
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "run_interrupt/v1",
          interrupt_id: "int-2",
          run_id: "run-2",
          thread_id: "thread-2",
          kind: "approval",
          risk: "medium",
          payload: { title: "edited" },
          status: "edited",
          decision: { action: "edit", payload: { title: "edited" } },
          decision_actor: "ui-user",
          decision_action: "edit",
          created_at: "2026-02-27T00:00:00Z",
          resolved_at: "2026-02-27T00:00:01Z",
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(new Response(JSON.stringify({ run_id: "run-2", status: "running" }), { status: 200 }))
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "inbox/v1",
          items: [],
          diagnostics: {
            cache: { hit: true, ttl_seconds: 30, key: "x" },
            rate_limit: { remaining: 100, reset_at: "", source: "github" },
            queries: { calls: 0, chunk_size: 5, chunks: [] },
          },
          summary: { count: 0, pm_bot_count: 0, github_count: 0 },
        }),
        { status: 200 },
      ),
    );

  render(<InboxPage />);
  await userEvent.click(await screen.findByRole("button", { name: "Edit" }));

  const resumeCall = mockedFetch.mock.calls.find(([url]) =>
    typeof url === "string" && url.endsWith("/runs/run-2/resume"),
  );
  expect(resumeCall).toBeTruthy();
  expect(resumeCall?.[1]).toEqual(
    expect.objectContaining({
      body: JSON.stringify({ decision: { action: "edit", edited_payload: { title: "edited" } }, actor: "ui-user" }),
      method: "POST",
    }),
  );
  expect(await screen.findByText("No inbox items.")).toBeTruthy();
});
