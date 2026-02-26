import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/inbox**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "inbox/v1",
        items: [
          {
            source: "pm_bot",
            item_type: "approval",
            id: "changeset:7",
            title: "Approve create_issue for phys-sims/phys-pipeline",
            repo: "phys-sims/phys-pipeline",
            url: "",
            state: "pending",
            priority: "",
            age_hours: 0,
            action: "approve",
            requires_internal_approval: true,
            stale: false,
            stale_reason: "",
            metadata: { changeset_id: 7, operation: "create_issue" },
          },
          {
            source: "github",
            item_type: "triage",
            id: "github:phys-sims/phys-pipeline#12",
            title: "Needs-human triage",
            repo: "phys-sims/phys-pipeline",
            url: "https://github.com/phys-sims/phys-pipeline/issues/12",
            state: "open",
            priority: "",
            age_hours: 0,
            action: "triage",
            requires_internal_approval: false,
            stale: false,
            stale_reason: "",
            metadata: { labels: ["needs-human"] },
          },
        ],
        diagnostics: {
          cache: { hit: false, ttl_seconds: 30, key: "k" },
          rate_limit: { remaining: 4999, reset_at: "", source: "github" },
          queries: { calls: 1, chunk_size: 5, chunks: [] },
        },
        summary: { count: 2, pm_bot_count: 1, github_count: 1 },
      }),
    });
  });

  await page.route("**/changesets/7/approve", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "applied" }),
    });
  });

  await page.route("**/graph/tree**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        root: {
          issue_ref: "draft:epic:root",
          title: "Root",
          type: "epic",
          provenance: "sub_issue",
          children: [
            {
              issue_ref: "draft:task:child",
              title: "Child",
              type: "task",
              provenance: "dependency_api",
              children: [],
            },
          ],
        },
        warnings: [{ code: "cycle_detected", message: "cycle" }],
      }),
    });
  });

  await page.route("**/graph/deps", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        nodes: [],
        edges: [],
        warnings: [{ code: "no_dependencies", message: "none" }],
        summary: { node_count: 2, edge_count: 1 },
      }),
    });
  });

  await page.route("**/report-ir/intake", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        draft_id: "draft-e2e-001",
        schema_version: "report_ir_draft/v1",
        draft: {
          schema_version: "report_ir/v1",
          report: {
            title: "Roadmap intake",
            generated_at: "2026-02-26",
            scope: { org: "phys-sims", repos: ["phys-sims/pm-bot"] },
          },
          epics: [{ stable_id: "epic:roadmap", title: "Roadmap", area: "triage", priority: "Triage" }],
          tasks: [
            {
              stable_id: "task:tests",
              title: "Add tests",
              area: "triage",
              priority: "Triage",
              epic_id: "epic:roadmap",
              blocked_by: [],
            },
          ],
        },
        validation: { errors: [], warnings: [] },
      }),
    });
  });

  await page.route("**/report-ir/confirm", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "confirmed",
        confirmation_id: "confirm-e2e-001",
        validation: { errors: [], warnings: [] },
        report_ir: { schema_version: "report_ir/v1" },
      }),
    });
  });

  await page.route("**/report-ir/preview", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "changeset_preview/v1",
        items: [
          {
            repo: "phys-sims/pm-bot",
            operation: "create_issue",
            item_type: "epic",
            stable_id: "epic:roadmap",
            target_ref: "",
            payload: {},
            idempotency_key: "preview-e2e-0",
          },
          {
            repo: "phys-sims/pm-bot",
            operation: "create_issue",
            item_type: "task",
            stable_id: "task:tests",
            target_ref: "",
            payload: {},
            idempotency_key: "preview-e2e-1",
          },
        ],
        dependency_preview: {
          repos: [
            {
              repo: "phys-sims/pm-bot",
              nodes: [
                {
                  stable_id: "epic:roadmap",
                  title: "Roadmap",
                  item_type: "epic",
                  parent_id: "",
                  blocked_by: [],
                  depends_on: [],
                },
                {
                  stable_id: "task:tests",
                  title: "Add tests",
                  item_type: "task",
                  parent_id: "epic:roadmap",
                  blocked_by: [],
                  depends_on: [],
                },
              ],
              edges: [{ edge_type: "parent_child", source: "epic:roadmap", target: "task:tests", provenance: "report_ir" }],
            },
          ],
        },
        summary: { count: 2, repos: ["phys-sims/pm-bot"], repo_count: 1 },
      }),
    });
  });

  await page.route("**/report-ir/propose", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "report_ir_proposal/v1",
        items: [
          {
            stable_id: "epic:roadmap",
            repo: "phys-sims/pm-bot",
            idempotency_key: "proposal-e2e-0",
            changeset: {
              id: 7,
              operation: "create_issue",
              repo: "phys-sims/pm-bot",
              payload: {},
              status: "pending_approval",
              requested_by: "ui-operator",
              approved_by: "",
              run_id: "run-ui-plan-intake",
              target_ref: "",
              idempotency_key: "proposal-e2e-0",
              reason_code: "",
              created_at: "2026-02-26T00:00:00Z",
              updated_at: "2026-02-26T00:00:00Z",
            },
          },
        ],
        summary: { count: 2 },
      }),
    });
  });
});

test("approve from inbox", async ({ page }) => {
  page.on("dialog", (dialog) => dialog.accept());
  await page.goto("/");
  await expect(page.getByText("Total: 2")).toBeVisible();
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByRole("status")).toContainText("Approved changeset #7");
});

test("render tree provenance and warnings", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Tree" }).click();
  await page.getByRole("button", { name: "Load graph" }).click();
  await expect(page.getByText("Root [sub_issue]")).toBeVisible();
  await expect(page.getByText("Child [dependency_api]")).toBeVisible();
  await expect(page.getByText(/cycle_detected: cycle/)).toBeVisible();
});

test("show denied approval error", async ({ page }) => {
  await page.route("**/changesets/7/approve", async (route) => {
    await route.fulfill({
      status: 403,
      contentType: "application/json",
      body: JSON.stringify({ error: "denied", reason_code: "operation_denylisted" }),
    });
  });
  page.on("dialog", (dialog) => dialog.accept());

  await page.goto("/");
  await page.getByRole("button", { name: "Approve" }).click();

  await expect(page.getByRole("status")).toContainText("operation_denylisted");
});

test("plan intake human-gated flow from natural text to proposed changesets", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Plan Intake" }).click();

  await page.getByRole("button", { name: /Draft from intake/ }).click();
  await expect(page.getByRole("status")).toContainText("Draft generated: draft-e2e-001");

  await page.getByRole("button", { name: /Confirm report_ir/ }).click();
  await expect(page.getByRole("status")).toContainText("ReportIR confirmed: confirm-e2e-001");

  await page.getByRole("button", { name: /Preview operations/ }).click();
  await expect(page.getByText("create_issue: 2")).toBeVisible();
  await expect(page.getByText("task: Add tests (task:tests)")).toBeVisible();

  await page.getByRole("button", { name: /Propose changesets/ }).click();
  await expect(page.getByRole("status")).toContainText("Proposed 2 approval-gated changesets.");
  await expect(page.getByText("Created changesets: 2")).toBeVisible();

  await page.getByRole("button", { name: "Inbox" }).click();
  await expect(page.getByText("Approve create_issue for phys-sims/phys-pipeline")).toBeVisible();
});
