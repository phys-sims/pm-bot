import { useState } from "react";
import { api, formatApiError, type AgentRunRecord } from "./api";

const APPROVE_REASON = "human_approved";

export function AgentRunsPage() {
  const [runId, setRunId] = useState("run-ui-001");
  const [intent, setIntent] = useState("Draft implementation plan");
  const [model, setModel] = useState("gpt-5");
  const [adapter, setAdapter] = useState("manual");
  const [createdBy, setCreatedBy] = useState("ui-operator");
  const [actor, setActor] = useState("ui-reviewer");
  const [workerId, setWorkerId] = useState("worker-ui-1");
  const [run, setRun] = useState<AgentRunRecord | null>(null);
  const [message, setMessage] = useState("");

  const propose = async () => {
    try {
      const proposed = await api.proposeAgentRun({
        created_by: createdBy,
        spec: {
          run_id: runId,
          model,
          intent,
          adapter,
          requires_approval: true,
        },
      });
      setRun(proposed);
      setMessage(`Proposed run ${proposed.run_id}.`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const transition = async (toStatus: "approved" | "rejected" | "cancelled", reasonCode: string) => {
    try {
      const updated = await api.transitionAgentRun({
        run_id: runId,
        to_status: toStatus,
        reason_code: reasonCode,
        actor,
      });
      setRun(updated);
      setMessage(`Run ${updated.run_id} transitioned to ${updated.status}.`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const claim = async () => {
    try {
      const response = await api.claimAgentRuns({ worker_id: workerId, limit: 1, lease_seconds: 30 });
      const matched = response.items.find((item) => item.run_id === runId);
      if (matched) {
        setRun(matched);
        setMessage(`Claimed run ${matched.run_id}.`);
      } else {
        setMessage(`No claimable run found for ${runId}.`);
      }
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const execute = async () => {
    try {
      const executed = await api.executeAgentRun({ run_id: runId, worker_id: workerId });
      setRun(executed);
      setMessage(`Run ${executed.run_id} execution status: ${executed.status}.`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const cancel = async () => {
    try {
      const cancelled = await api.cancelAgentRun({ run_id: runId, actor });
      setRun(cancelled);
      setMessage(`Run ${cancelled.run_id} cancelled.`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const canApprove = run?.status === "proposed";
  const canExecute = run?.status === "approved" && run.claimed_by === workerId;

  return (
    <section>
      <h2>Agent Runs</h2>
      <p>Propose approval-gated runs and enforce state-aware execution controls.</p>
      <div style={{ display: "grid", gap: 8, maxWidth: 460 }}>
        <label>
          Run ID:
          <input value={runId} onChange={(event) => setRunId(event.target.value)} />
        </label>
        <label>
          Intent:
          <input value={intent} onChange={(event) => setIntent(event.target.value)} />
        </label>
        <label>
          Model:
          <input value={model} onChange={(event) => setModel(event.target.value)} />
        </label>
        <label>
          Adapter:
          <select value={adapter} onChange={(event) => setAdapter(event.target.value)}>
            <option value="manual">manual</option>
            <option value="provider_stub">provider_stub</option>
          </select>
        </label>
        <label>
          Created by:
          <input value={createdBy} onChange={(event) => setCreatedBy(event.target.value)} />
        </label>
        <label>
          Actor:
          <input value={actor} onChange={(event) => setActor(event.target.value)} />
        </label>
        <label>
          Worker ID:
          <input value={workerId} onChange={(event) => setWorkerId(event.target.value)} />
        </label>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
        <button onClick={() => void propose()}>Propose run</button>
        <button disabled={!canApprove} onClick={() => void transition("approved", APPROVE_REASON)}>
          Approve run
        </button>
        <button disabled={!canApprove} onClick={() => void transition("rejected", "human_rejected")}>
          Reject run
        </button>
        <button onClick={() => void claim()}>Claim run</button>
        <button disabled={!canExecute} onClick={() => void execute()}>
          Execute claimed run
        </button>
        <button disabled={!run || run.status === "completed" || run.status === "cancelled" || run.status === "failed"} onClick={() => void cancel()}>
          Cancel run
        </button>
      </div>

      {!canExecute && (
        <p>
          Execute remains disabled until run status is <code>approved</code> and the run is claimed by the current worker.
        </p>
      )}

      {message && <p role="status">{message}</p>}

      {run && (
        <article>
          <h3>Run details</h3>
          <ul>
            <li>Run ID: {run.run_id}</li>
            <li>Status: {run.status}</li>
            <li>Status reason: {run.status_reason}</li>
            <li>Adapter: {run.adapter_name}</li>
            <li>Claimed by: {run.claimed_by || "(none)"}</li>
            <li>Job ID: {run.job_id || "(none)"}</li>
            <li>Retries: {run.retry_count}/{run.max_retries}</li>
            <li>Last error: {run.last_error || "(none)"}</li>
          </ul>
        </article>
      )}
    </section>
  );
}
