import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { TreePage } from "./TreePage";

vi.stubGlobal("fetch", vi.fn());

const mockedFetch = vi.mocked(fetch);

beforeEach(() => {
  mockedFetch.mockReset();
});

test("renders tree and warnings", async () => {
  mockedFetch
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          root: { issue_ref: "draft:epic:root", title: "Root", type: "epic", provenance: "sub_issue", children: [] },
          warnings: [{ code: "conflicting_parent_edge", message: "warn" }],
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ nodes: [], edges: [], warnings: [], summary: { node_count: 1, edge_count: 0 } }), { status: 200 }),
    );

  render(<TreePage />);
  await userEvent.click(screen.getByRole("button", { name: "Load graph" }));

  expect(await screen.findByText(/Dependency summary: 1 nodes/)).toBeInTheDocument();
  expect(await screen.findByText(/conflicting_parent_edge/)).toBeInTheDocument();
});
