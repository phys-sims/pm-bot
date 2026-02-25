import { useEffect, useMemo, useState } from "react";
import { api, formatApiError, type InboxItem } from "./api";

type SourceTab = "all" | "pm_bot" | "github";

export function InboxPage() {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [message, setMessage] = useState("");
  const [selectedSource, setSelectedSource] = useState<SourceTab>("all");
  const [selectedAction, setSelectedAction] = useState<string>("all");
  const [diagnostics, setDiagnostics] = useState<{
    cache: { hit: boolean; ttl_seconds: number; key: string };
    rate_limit: { remaining: number; reset_at: string; source: string };
    queries: { calls: number; chunk_size: number; chunks: Array<{ repo: string; labels: string[]; q: string }> };
  } | null>(null);

  const load = async () => {
    try {
      const response = await api.unifiedInbox({ labels: ["needs-human", "needs-triage", "status:review"] });
      setItems(response.items);
      setDiagnostics(response.diagnostics);
      setMessage("");
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const approve = async (id: number) => {
    const confirmed = window.confirm(`Approve changeset #${id}?`);
    if (!confirmed) {
      return;
    }
    try {
      await api.approveChangeset(id, "ui-user");
      setMessage(`Approved changeset #${id}`);
      await load();
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const filtered = useMemo(() => {
    return items.filter((item) => {
      if (selectedSource !== "all" && item.source !== selectedSource) {
        return false;
      }
      if (selectedAction !== "all" && item.action !== selectedAction) {
        return false;
      }
      return true;
    });
  }, [items, selectedAction, selectedSource]);

  return (
    <section>
      <h2>Unified Inbox</h2>
      <p>Total: {items.length}</p>
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <button onClick={() => setSelectedSource("all")}>All</button>
        <button onClick={() => setSelectedSource("pm_bot")}>pm-bot approvals</button>
        <button onClick={() => setSelectedSource("github")}>GitHub triage/review</button>
      </div>
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <label>
          Action:
          <select value={selectedAction} onChange={(event) => setSelectedAction(event.target.value)}>
            <option value="all">all</option>
            <option value="approve">approve</option>
            <option value="review">review</option>
            <option value="triage">triage</option>
          </select>
        </label>
      </div>
      {message && <div role="status">{message}</div>}
      {diagnostics && (
        <p>
          cache: {diagnostics.cache.hit ? "hit" : "miss"}; github calls: {diagnostics.queries.calls}; rate-limit remaining: {diagnostics.rate_limit.remaining}
        </p>
      )}
      {filtered.length === 0 ? (
        <p>No inbox items.</p>
      ) : (
        <ul>
          {filtered.map((item) => {
            const changesetId = Number(item.metadata.changeset_id ?? 0);
            return (
              <li key={item.id}>
                <strong>{item.source}</strong> {item.title} ({item.action}) {item.stale ? `[stale: ${item.stale_reason}]` : ""}{" "}
                {item.requires_internal_approval ? (
                  <button onClick={() => void approve(changesetId)}>Approve</button>
                ) : (
                  <a href={item.url} target="_blank" rel="noreferrer">
                    Open in GitHub
                  </a>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
