import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { ContextPackPage } from "./ContextPackPage";

vi.stubGlobal("fetch", vi.fn());

const mockedFetch = vi.mocked(fetch);

beforeEach(() => {
  mockedFetch.mockReset();
});

test("builds context pack and shows hash/budget manifest summary", async () => {
  mockedFetch.mockResolvedValueOnce(
    new Response(
      JSON.stringify({
        schema_version: "context_pack/v2",
        profile: "pm-drafting",
        hash: "abc123",
        budget: { max_chars: 1200, used_chars: 640, strategy: "ranked_trim" },
        manifest: {
          included_segments: ["a", "b"],
          excluded_segments: ["c"],
          exclusion_reasons: { budget_exceeded: 1 },
          redaction_counts: { total: 0, by_category: {} },
        },
      }),
      { status: 200 },
    ),
  );

  render(<ContextPackPage />);
  await userEvent.click(screen.getByRole("button", { name: "Build context pack" }));

  expect(await screen.findByText(/Context pack generated/)).toBeTruthy();
  expect(await screen.findByText(/Hash: abc123/)).toBeTruthy();
  expect(await screen.findByText(/Budget: 640\/1200/)).toBeTruthy();
});
