import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { PlanIntakePage } from "./PlanIntakePage";

vi.stubGlobal("fetch", vi.fn());
const mockedFetch = vi.mocked(fetch);

beforeEach(() => {
  cleanup();
  mockedFetch.mockReset();
});

const BASE_DRAFT = {
  schema_version: "report_ir/v1",
  report: { title: "Plan", generated_at: "2026-02-26", scope: { org: "phys-sims", repos: ["phys-sims/pm-bot"] } },
  epics: [{ stable_id: "epic:plan", title: "Plan", area: "triage", priority: "Triage" }],
  features: [
    {
      stable_id: "feat:add-ui",
      title: "Add UI",
      area: "triage",
      priority: "Triage",
      epic_id: "epic:plan",
    },
  ],
  tasks: [
    {
      stable_id: "task:add-tests",
      title: "Add Tests",
      area: "triage",
      priority: "Triage",
      feature_id: "feat:add-ui",
      blocked_by: ["task:backend-ready"],
    },
  ],
};

function queueSuccessfulPlanFlowResponses(): void {
  mockedFetch
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          draft_id: "abc123",
          schema_version: "report_ir_draft/v1",
          draft: BASE_DRAFT,
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
              item_type: "epic",
              stable_id: "epic:plan",
              target_ref: "",
              payload: {},
              idempotency_key: "k0",
            },
            {
              repo: "phys-sims/pm-bot",
              operation: "create_issue",
              item_type: "feature",
              stable_id: "feat:add-ui",
              target_ref: "",
              payload: {},
              idempotency_key: "k1",
            },
            {
              repo: "phys-sims/pm-bot",
              operation: "create_issue",
              item_type: "task",
              stable_id: "task:add-tests",
              target_ref: "",
              payload: {},
              idempotency_key: "k2",
            },
          ],
          dependency_preview: {
            repos: [
              {
                repo: "phys-sims/pm-bot",
                nodes: [
                  {
                    stable_id: "epic:plan",
                    title: "Plan",
                    item_type: "epic",
                    parent_id: "",
                    blocked_by: [],
                    depends_on: [],
                  },
                  {
                    stable_id: "feat:add-ui",
                    title: "Add UI",
                    item_type: "feature",
                    parent_id: "epic:plan",
                    blocked_by: [],
                    depends_on: [],
                  },
                  {
                    stable_id: "task:add-tests",
                    title: "Add Tests",
                    item_type: "task",
                    parent_id: "feat:add-ui",
                    blocked_by: ["task:backend-ready"],
                    depends_on: [],
                  },
                ],
                edges: [
                  { edge_type: "parent_child", source: "epic:plan", target: "feat:add-ui", provenance: "report_ir" },
                  { edge_type: "parent_child", source: "feat:add-ui", target: "task:add-tests", provenance: "report_ir" },
                  { edge_type: "blocked_by", source: "task:add-tests", target: "task:backend-ready", provenance: "report_ir" },
                ],
              },
            ],
          },
          summary: { count: 3, repos: ["phys-sims/pm-bot"], repo_count: 1 },
        }),
        { status: 200 },
      ),
    );
}

test("runs intake -> confirm -> preview -> propose guided flow", async () => {
  queueSuccessfulPlanFlowResponses();
  mockedFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          schema_version: "report_ir_proposal/v1",
          items: [],
          summary: { count: 3 },
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
  expect(await screen.findByText(/Total operations: 3/)).toBeTruthy();
  expect(await screen.findByText(/create_issue: 3/)).toBeTruthy();
  expect(await screen.findByText(/task: Add Tests \(task:add-tests\)/)).toBeTruthy();
  expect(await screen.findByText(/blocked by task:backend-ready/)).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: /Propose changesets/ }));
  expect(await screen.findByText(/Created changesets: 3/)).toBeTruthy();
});

test("confirms using edited report_ir JSON", async () => {
  queueSuccessfulPlanFlowResponses();

  render(<PlanIntakePage />);
  await userEvent.click(screen.getByRole("button", { name: /Draft from intake/ }));

  const reportEditor = screen.getByRole("textbox", { name: /Editable report_ir JSON/i });
  const editedDraft = {
    ...BASE_DRAFT,
    report: { ...BASE_DRAFT.report, title: "Edited plan title" },
  };
  fireEvent.change(reportEditor, { target: { value: JSON.stringify(editedDraft) } });

  await userEvent.click(screen.getByRole("button", { name: /Confirm report_ir/ }));
  expect(await screen.findByText(/ReportIR confirmed/)).toBeTruthy();

  const confirmRequest = mockedFetch.mock.calls[1];
  const confirmPayload = JSON.parse(String((confirmRequest[1] as RequestInit).body));
  expect(confirmPayload.report_ir.report.title).toBe("Edited plan title");
});

test("shows propose error when API request fails", async () => {
  queueSuccessfulPlanFlowResponses();
  mockedFetch.mockResolvedValueOnce(
    new Response(JSON.stringify({ error: "denied", reason_code: "approval_required" }), { status: 403 }),
  );

  render(<PlanIntakePage />);
  await userEvent.click(screen.getByRole("button", { name: /Draft from intake/ }));
  await userEvent.click(screen.getByRole("button", { name: /Confirm report_ir/ }));
  await userEvent.click(screen.getByRole("button", { name: /Preview operations/ }));
  await userEvent.click(screen.getByRole("button", { name: /Propose changesets/ }));

  expect((await screen.findByRole("status")).textContent).toMatch(/Error: approval_required/i);
});

test("blocks proposing changesets when dependency preview has validation errors", async () => {
  mockedFetch
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          draft_id: "abc123",
          schema_version: "report_ir_draft/v1",
          draft: {
            schema_version: "report_ir/v1",
            report: { title: "Plan", generated_at: "2026-02-26", scope: { org: "phys-sims", repos: ["phys-sims/pm-bot"] } },
            features: [{ stable_id: "feat:add-ui", title: "Add UI", area: "triage", priority: "Triage", epic_id: "epic:missing" }],
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
              item_type: "feature",
              stable_id: "feat:add-ui",
              target_ref: "",
              payload: {},
              idempotency_key: "k1",
            },
          ],
          dependency_preview: {
            repos: [
              {
                repo: "phys-sims/pm-bot",
                nodes: [
                  {
                    stable_id: "feat:add-ui",
                    title: "Add UI",
                    item_type: "feature",
                    parent_id: "epic:missing",
                    blocked_by: [],
                    depends_on: [],
                  },
                ],
                edges: [],
              },
            ],
          },
          summary: { count: 1, repos: ["phys-sims/pm-bot"], repo_count: 1 },
        }),
        { status: 200 },
      ),
    );

  render(<PlanIntakePage />);

  await userEvent.click(screen.getByRole("button", { name: /Draft from intake/ }));
  await userEvent.click(screen.getByRole("button", { name: /Confirm report_ir/ }));
  await userEvent.click(screen.getByRole("button", { name: /Preview operations/ }));

  expect(await screen.findByText(/Errors \(1\)/)).toBeTruthy();
  expect(await screen.findByText(/references missing parent epic:missing/)).toBeTruthy();
  expect((screen.getByRole("button", { name: /Propose changesets/ }) as HTMLButtonElement).disabled).toBe(true);
});
