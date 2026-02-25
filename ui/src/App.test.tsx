import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { App } from "./App";

vi.stubGlobal("fetch", vi.fn());

const mockedFetch = vi.mocked(fetch);

beforeEach(() => {
  mockedFetch.mockReset();
  mockedFetch.mockResolvedValue(
    new Response(
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
    ),
  );
});

test("adds agent-runs and context-pack routes to app shell", async () => {
  render(<App />);

  expect(await screen.findByRole("heading", { name: "Unified Inbox" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Agent Runs" }));
  expect(await screen.findByRole("heading", { name: "Agent Runs" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Context Pack" }));
  expect(await screen.findByRole("heading", { name: "Context Pack" })).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: "Tree" }));
  expect(await screen.findByRole("heading", { name: "Tree and Dependencies" })).toBeTruthy();
});
