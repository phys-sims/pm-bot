# Contract: RunInterrupt/v1
> **Audience:** Contributors implementing run interrupt/artifact control-plane contracts.
> **Depth:** L3 (normative contract).
> **Source of truth:** Authoritative interrupt contract for run-level human decisions.

Interrupt envelope for human approval/rejection/edit decisions tied to a run/thread.

Required fields: `interrupt_id`, `run_id`, `thread_id`, `kind`, `risk`, `payload`, `status`, `decision`.

- `status`: `pending|approved|rejected|edited`
- `risk`: `low|medium|high`
