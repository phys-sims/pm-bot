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
