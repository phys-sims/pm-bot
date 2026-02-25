import { useEffect, useState } from "react";
import { api, formatApiError, type AuditChainEvent, type AuditIncidentBundleResponse, type AuditRollupsResponse } from "./api";

export function AuditOpsPage() {
  const [runId, setRunId] = useState("");
  const [actor, setActor] = useState("");
  const [repo, setRepo] = useState("");
  const [eventType, setEventType] = useState("");
  const [timeline, setTimeline] = useState<AuditChainEvent[]>([]);
  const [rollups, setRollups] = useState<AuditRollupsResponse | null>(null);
  const [bundle, setBundle] = useState<AuditIncidentBundleResponse | null>(null);
  const [message, setMessage] = useState("");

  const refresh = async () => {
    try {
      const [chainResponse, rollupResponse] = await Promise.all([
        api.auditChain({ run_id: runId, actor, repo, event_type: eventType }),
        api.auditRollups({ run_id: runId }),
      ]);
      setTimeline(chainResponse.items);
      setRollups(rollupResponse);
      setMessage(`Loaded ${chainResponse.summary.count} timeline event(s).`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const exportBundle = async () => {
    try {
      const response = await api.auditIncidentBundle({ run_id: runId, actor });
      setBundle(response);
      setMessage(`Exported incident bundle with ${response.chain.summary.count} event(s).`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  return (
    <section>
      <h2>Audit Ops</h2>
      <p>Trace multi-agent chains by run and inspect rollups for retries, denials, and dead letters.</p>
      <div style={{ display: "grid", gap: 8, maxWidth: 560 }}>
        <label>
          Run ID:
          <input value={runId} onChange={(event) => setRunId(event.target.value)} />
        </label>
        <label>
          Actor:
          <input value={actor} onChange={(event) => setActor(event.target.value)} />
        </label>
        <label>
          Repo:
          <input value={repo} onChange={(event) => setRepo(event.target.value)} />
        </label>
        <label>
          Event type:
          <input value={eventType} onChange={(event) => setEventType(event.target.value)} />
        </label>
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button onClick={() => void refresh()}>Refresh timeline + rollups</button>
        <button onClick={() => void exportBundle()}>Export incident bundle</button>
      </div>

      {message && <p role="status">{message}</p>}

      {rollups && (
        <article>
          <h3>Multi-agent rollups</h3>
          <ul>
            <li>Sample size: {rollups.summary.sample_size}</li>
            <li>Completion rate: {rollups.summary.completion_rate}</li>
            <li>Retries: {rollups.summary.retry_count}</li>
            <li>Dead-lettered: {rollups.summary.dead_letter_count}</li>
            <li>Denials: {rollups.summary.denial_count}</li>
            <li>Average queue age (s): {rollups.summary.average_queue_age_seconds}</li>
          </ul>
        </article>
      )}

      <article>
        <h3>Correlated timeline</h3>
        {timeline.length === 0 ? (
          <p>No events matched filters.</p>
        ) : (
          <ul>
            {timeline.map((item) => (
              <li key={item.id}>
                #{item.id} [{item.event_type}] run={String(item.payload.run_id || "(none)")} repo={String(item.payload.repo || item.payload.target_repo || "(none)")}
              </li>
            ))}
          </ul>
        )}
      </article>

      <article>
        <h3>Runbook hooks</h3>
        {bundle ? (
          <ul>
            {Object.entries(bundle.runbook_hooks).map(([key, path]) => (
              <li key={key}>
                {key}: <code>{path}</code>
              </li>
            ))}
          </ul>
        ) : (
          <p>Export a bundle to view runbook links and incident payload.</p>
        )}
      </article>
    </section>
  );
}
