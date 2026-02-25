import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { AgentRunsPage } from "./AgentRunsPage";

vi.stubGlobal("fetch", vi.fn());
const mockedFetch = vi.mocked(fetch);

beforeEach(() => {
  mockedFetch.mockReset();
});

test("keeps execute disabled until approved and claimed by worker", async () => {
  mockedFetch
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          run_id: "run-ui-001",
          status: "proposed",
          status_reason: "run_created",
          created_by: "ui-operator",
          intent: "Draft implementation plan",
          model: "gpt-5",
          adapter_name: "manual",
          claimed_by: "",
          retry_count: 0,
          max_retries: 2,
          last_error: "",
          job_id: "",
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [], summary: { count: 0 } }), { status: 200 }),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          run_id: "run-ui-001",
          status: "approved",
          status_reason: "human_approved",
          created_by: "ui-operator",
          intent: "Draft implementation plan",
          model: "gpt-5",
          adapter_name: "manual",
          claimed_by: "",
          retry_count: 0,
          max_retries: 2,
          last_error: "",
          job_id: "",
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              run_id: "run-ui-001",
              status: "approved",
              status_reason: "human_approved",
              created_by: "ui-operator",
              intent: "Draft implementation plan",
              model: "gpt-5",
              adapter_name: "manual",
              claimed_by: "worker-ui-1",
              retry_count: 0,
              max_retries: 2,
              last_error: "",
              job_id: "job-1",
            },
          ],
          summary: { count: 1 },
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          run_id: "run-ui-001",
          status: "completed",
          status_reason: "adapter_completed",
          created_by: "ui-operator",
          intent: "Draft implementation plan",
          model: "gpt-5",
          adapter_name: "manual",
          claimed_by: "",
          retry_count: 0,
          max_retries: 2,
          last_error: "",
          job_id: "job-1",
        }),
        { status: 200 },
      ),
    );

  render(<AgentRunsPage />);

  const executeButton = screen.getByRole("button", { name: "Execute claimed run" });
  expect(executeButton).toBeDisabled();

  await userEvent.click(screen.getByRole("button", { name: "Propose run" }));
  expect(executeButton).toBeDisabled();

  await userEvent.click(screen.getByRole("button", { name: "Claim run" }));
  expect(await screen.findByText(/No claimable run found/)).toBeTruthy();
  expect(executeButton).toBeDisabled();

  await userEvent.click(screen.getByRole("button", { name: "Approve run" }));
  expect(executeButton).toBeDisabled();

  await userEvent.click(screen.getByRole("button", { name: "Claim run" }));
  expect(await screen.findByText(/Claimed run run-ui-001/)).toBeTruthy();
  expect(executeButton).toBeEnabled();

  await userEvent.click(executeButton);
  expect(await screen.findByText(/execution status: completed/)).toBeTruthy();
});

test("renders normalized reason code on API errors", async () => {
  mockedFetch.mockResolvedValueOnce(
    new Response(JSON.stringify({ error: "unknown_adapter", reason_code: "unknown_adapter" }), {
      status: 400,
    }),
  );

  render(<AgentRunsPage />);
  await userEvent.selectOptions(screen.getByRole("combobox"), "provider_stub");
  await userEvent.click(screen.getByRole("button", { name: "Propose run" }));

  expect(await screen.findByText(/Error: unknown_adapter/)).toBeTruthy();
});
