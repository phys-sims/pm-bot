import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { RunDetailPage } from "./RunDetailPage";

vi.stubGlobal("fetch", vi.fn());
const mockedFetch = vi.mocked(fetch);

beforeEach(() => {
  mockedFetch.mockReset();
});

test("loads run details, views artifact, and approves changeset apply", async () => {
  mockedFetch
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          run_id: "run-ui-001",
          status: "blocked",
          status_reason: "interrupt_pending",
          created_by: "ui",
          intent: "test",
          model: "gpt-5",
          adapter_name: "manual",
          claimed_by: "",
          retry_count: 0,
          max_retries: 2,
          last_error: "",
          job_id: "",
          artifact_paths: [],
          budgets: { max_total_tokens: 100, max_tool_calls: 2, max_wall_seconds: 60 },
          artifacts: [
            {
              schema_version: "run_artifact/v1",
              artifact_id: "a1",
              run_id: "run-ui-001",
              kind: "file",
              uri: "file:///tmp/changeset_bundle.json",
              metadata: { changeset_id: 77 },
              created_at: "2026-02-27T00:00:00Z",
            },
          ],
          interrupts: [],
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "artifact_view/v1",
          uri: "/tmp/changeset_bundle.json",
          view_type: "json",
          size_bytes: 8,
          content: '{"ok":1}',
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(new Response(JSON.stringify({ status: "applied" }), { status: 200 }))
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          run_id: "run-ui-001",
          status: "running",
          status_reason: "resumed",
          created_by: "ui",
          intent: "test",
          model: "gpt-5",
          adapter_name: "manual",
          claimed_by: "",
          retry_count: 0,
          max_retries: 2,
          last_error: "",
          job_id: "",
          artifact_paths: [],
          budgets: { max_total_tokens: 100, max_tool_calls: 2, max_wall_seconds: 60 },
          artifacts: [],
          interrupts: [],
        }),
        { status: 200 },
      ),
    );

  render(<RunDetailPage />);
  await userEvent.click(screen.getByRole("button", { name: "Load run" }));
  expect(await screen.findByText(/State: ready/)).toBeTruthy();
  await userEvent.click(screen.getByRole("button", { name: "View" }));
  expect(await screen.findByText(/\{"ok":1\}/)).toBeTruthy();
  await userEvent.click(screen.getByRole("button", { name: "Approve changeset apply" }));
  expect(await screen.findByText(/Approved changeset #77/)).toBeTruthy();
});
