import { useState } from "react";
import { api, formatApiError, type ContextPackResponse } from "./api";

export function ContextPackPage() {
  const [issueRef, setIssueRef] = useState("draft:epic:root");
  const [budget, setBudget] = useState(1200);
  const [requestedBy, setRequestedBy] = useState("ui-operator");
  const [runId, setRunId] = useState("run-ui-context-pack");
  const [result, setResult] = useState<ContextPackResponse | null>(null);
  const [message, setMessage] = useState("");

  const buildContextPack = async () => {
    try {
      const response = await api.contextPack({
        issue_ref: issueRef,
        budget,
        profile: "pm-drafting",
        schema_version: "context_pack/v2",
        requested_by: requestedBy,
        run_id: runId,
      });
      setResult(response);
      setMessage("Context pack generated.");
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  return (
    <section>
      <h2>Context Pack</h2>
      <p>Build deterministic context packs and inspect hash/budget metadata.</p>
      <div style={{ display: "grid", gap: 8, maxWidth: 460 }}>
        <label>
          Issue ref:
          <input value={issueRef} onChange={(event) => setIssueRef(event.target.value)} />
        </label>
        <label>
          Budget (chars):
          <input type="number" min={100} value={budget} onChange={(event) => setBudget(Number(event.target.value))} />
        </label>
        <label>
          Requested by:
          <input value={requestedBy} onChange={(event) => setRequestedBy(event.target.value)} />
        </label>
        <label>
          Run ID:
          <input value={runId} onChange={(event) => setRunId(event.target.value)} />
        </label>
      </div>
      <button style={{ marginTop: 8 }} onClick={() => void buildContextPack()}>
        Build context pack
      </button>
      {message && <p role="status">{message}</p>}
      {result && (
        <article>
          <h3>Context pack summary</h3>
          <ul>
            <li>Schema: {result.schema_version}</li>
            <li>Profile: {result.profile}</li>
            <li>Hash: {result.hash}</li>
            <li>
              Budget: {result.budget.used_chars}/{result.budget.max_chars} ({result.budget.strategy})
            </li>
            <li>Included segments: {result.manifest.included_segments.length}</li>
            <li>Excluded segments: {result.manifest.excluded_segments.length}</li>
            <li>Redactions: {result.manifest.redaction_counts.total}</li>
          </ul>
        </article>
      )}
    </section>
  );
}
