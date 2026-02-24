import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/changesets/pending", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [{ id: 7, operation: "create_issue", repo: "phys-sims/phys-pipeline", status: "pending" }],
        summary: { count: 1 },
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
  await expect(page.getByText("Pending: 1")).toBeVisible();
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
