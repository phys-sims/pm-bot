# Runbook: Plan Intake → Inbox Approval/Apply E2E Evidence

## Purpose

Provide an auditable, reproducible path that starts in `ui/src/PlanIntakePage.tsx` and proves generated proposals are visible/actionable in Inbox approval/apply flow.

## Automated evidence source

Primary evidence is an integration-style UI test in `ui/src/App.test.tsx`:

- Test name: `runs intake-to-proposal flow and approves generated changeset from inbox`
- Coverage path:
  1. Navigate to **Plan Intake** route.
  2. Execute intake steps: draft → confirm → preview → propose.
  3. Assert proposal summary shows created changesets.
  4. Navigate to **Inbox**.
  5. Assert pending approval item is visible.
  6. Click approve and assert apply result is visible plus inbox drains to zero.

## How to run

```bash
npm --prefix ui test -- --run ui/src/App.test.tsx
```

## What to verify in output

- The E2E test above reports `PASS`.
- No failing assertions in route transitions or inbox approval/apply assertions.

## Traceability links

- Flow entry component: `ui/src/PlanIntakePage.tsx`
- Integration evidence test: `ui/src/App.test.tsx`
- v6 closure tracker: `docs/roadmaps/agent-roadmap-v6-multi-repo-orchestration.md`
