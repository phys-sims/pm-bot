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

test("loads pending changesets and approves one", async () => {
  mockedFetch
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [{ id: 1, operation: "create_issue", repo: "r" }], summary: { count: 1 } }), { status: 200 }),
    )
    .mockResolvedValueOnce(new Response(JSON.stringify({ status: "applied" }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ items: [], summary: { count: 0 } }), { status: 200 }));

  render(<InboxPage />);

  expect(await screen.findByText(/Pending: 1/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Approve" }));

  expect(await screen.findByText("Approved changeset #1")).toBeInTheDocument();
});
