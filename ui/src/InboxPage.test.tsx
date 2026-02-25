import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { InboxPage } from "./InboxPage";

vi.stubGlobal("fetch", vi.fn());

const mockedFetch = vi.mocked(fetch);

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
  await userEvent.click(screen.getByRole("button", { name: "Approve" }));

  expect(await screen.findByText(/Total: 0/)).toBeTruthy();
  expect(await screen.findByText("No inbox items.")).toBeTruthy();
  expect(mockedFetch).toHaveBeenCalledTimes(3);
});
