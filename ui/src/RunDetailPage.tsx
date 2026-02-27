import { useState } from "react";
import { api, formatApiError, type ArtifactViewResponse, type RunDetailsResponse } from "./api";

export function RunDetailPage() {
  const [runId, setRunId] = useState("run-ui-001");
  const [run, setRun] = useState<RunDetailsResponse | null>(null);
  const [artifactView, setArtifactView] = useState<ArtifactViewResponse | null>(null);
  const [selectedArtifactUri, setSelectedArtifactUri] = useState("");
  const [loadingState, setLoadingState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [message, setMessage] = useState("");

  const load = async () => {
    try {
      setLoadingState("loading");
      const details = await api.runDetails(runId);
      setRun(details);
      setLoadingState("ready");
      setMessage("");
    } catch (error) {
      setLoadingState("error");
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const loadArtifact = async (uri: string) => {
    try {
      setSelectedArtifactUri(uri);
      setArtifactView(await api.artifactView(uri));
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const approveChangeset = async () => {
    if (!run) return;
    const maybe = run.artifacts.find((item) => item.uri.includes("changeset"));
    const id = Number((maybe?.metadata?.changeset_id as number | undefined) ?? 0);
    if (!id) {
      setMessage("Error: no changeset artifact id found");
      return;
    }
    try {
      await api.approveChangeset(id, "ui-user");
      await load();
      setMessage(`Approved changeset #${id}`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  return (
    <section>
      <h2>Run Detail</h2>
      <p>Deterministic states: idle, loading, ready, error.</p>
      <label>
        Run ID:
        <input value={runId} onChange={(event) => setRunId(event.target.value)} />
      </label>
      <button disabled={loadingState === "loading"} onClick={() => void load()}>
        {loadingState === "loading" ? "Loading run..." : "Load run"}
      </button>
      {message && <p role="status">{message}</p>}
      <p>State: {loadingState}</p>

      {run && (
        <>
          <article>
            <h3>Run status and budgets</h3>
            <ul>
              <li>Status: {run.status}</li>
              <li>Reason: {run.status_reason}</li>
              <li>Model: {run.model}</li>
              <li>Budget max tokens: {String(run.budgets.max_total_tokens ?? "n/a")}</li>
              <li>Budget max tool calls: {String(run.budgets.max_tool_calls ?? "n/a")}</li>
              <li>Budget max wall seconds: {String(run.budgets.max_wall_seconds ?? "n/a")}</li>
            </ul>
          </article>

          <article>
            <h3>Artifacts</h3>
            {run.artifacts.length === 0 ? (
              <p>No artifacts.</p>
            ) : (
              <ul>
                {run.artifacts.map((item) => (
                  <li key={item.artifact_id}>
                    {item.kind}: {item.uri}
                    <button onClick={() => void loadArtifact(item.uri)}>View</button>
                  </li>
                ))}
              </ul>
            )}
            <button onClick={() => void approveChangeset()}>Approve changeset apply</button>
          </article>

          <article>
            <h3>Audit timeline (ordered events)</h3>
            {run.interrupts.length === 0 ? (
              <p>No interrupts.</p>
            ) : (
              <ol>
                {run.interrupts.map((item) => (
                  <li key={item.interrupt_id}>
                    {item.created_at} — {item.kind} ({item.status})
                  </li>
                ))}
              </ol>
            )}
          </article>
        </>
      )}

      {artifactView && (
        <article>
          <h3>Artifact viewer ({artifactView.view_type})</h3>
          <p>
            URI: {selectedArtifactUri} ({artifactView.size_bytes} bytes)
          </p>
          <pre style={{ maxHeight: 320, overflow: "auto", background: "#f4f4f4", padding: 8 }}>{artifactView.content}</pre>
        </article>
      )}
    </section>
  );
}
