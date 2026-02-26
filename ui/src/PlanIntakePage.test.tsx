import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { PlanIntakePage } from "./PlanIntakePage";

vi.stubGlobal("fetch", vi.fn());
const mockedFetch = vi.mocked(fetch);

beforeEach(() => {
  mockedFetch.mockReset();
});

test("runs intake -> confirm -> preview -> propose guided flow", async () => {
  mockedFetch
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          draft_id: "abc123",
          schema_version: "report_ir_draft/v1",
          draft: {
            schema_version: "report_ir/v1",
            report: { title: "Plan", generated_at: "2026-02-26", scope: { org: "phys-sims", repos: ["phys-sims/pm-bot"] } },
            features: [{ stable_id: "feat:add-ui", title: "Add UI", area: "triage", priority: "Triage" }],
          },
          validation: { errors: [], warnings: [] },
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          status: "confirmed",
          confirmation_id: "confirm-2026-02-26-plan",
          validation: { errors: [], warnings: [] },
          report_ir: { schema_version: "report_ir/v1" },
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "changeset_preview/v1",
          items: [
            {
              repo: "phys-sims/pm-bot",
              operation: "create_issue",
              stable_id: "feat:add-ui",
              target_ref: "",
              payload: {},
              idempotency_key: "k1",
            },
            {
              repo: "phys-sims/pm-bot",
              operation: "create_issue",
              stable_id: "feat:add-tests",
              target_ref: "",
              payload: {},
              idempotency_key: "k2",
            },
          ],
          summary: { count: 2, repos: ["phys-sims/pm-bot"], repo_count: 1 },
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "report_ir_proposal/v1",
          items: [],
          summary: { count: 2 },
        }),
        { status: 200 },
      ),
    );

  render(<PlanIntakePage />);

  await userEvent.click(screen.getByRole("button", { name: /Draft from intake/ }));
  expect(await screen.findByText(/Draft generated: abc123/)).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: /Confirm report_ir/ }));
  expect(await screen.findByText(/ReportIR confirmed/)).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: /Preview operations/ }));
  expect(await screen.findByText(/Total operations: 2/)).toBeTruthy();
  expect(await screen.findByText(/create_issue: 2/)).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: /Propose changesets/ }));
  expect(await screen.findByText(/Created changesets: 2/)).toBeTruthy();
});
