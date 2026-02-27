import { useEffect, useState } from "react";
import { api, formatApiError, type RepoRegistryEntry, type RepoSyncStatusResponse } from "./api";

export function RepoDashboardPage() {
  const [repos, setRepos] = useState<RepoRegistryEntry[]>([]);
  const [statuses, setStatuses] = useState<Record<number, RepoSyncStatusResponse>>({});
  const [message, setMessage] = useState("");

  const load = async () => {
    try {
      const response = await api.listRepos();
      setRepos(response.items);
      const statusRows = await Promise.all(response.items.map((repo) => api.repoSyncStatus(repo.id)));
      setStatuses(Object.fromEntries(statusRows.map((row) => [row.repo_id, row])));
      setMessage("");
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const syncNow = async (repoId: number) => {
    try {
      await api.syncRepo(repoId);
      await load();
      setMessage(`Synced repo #${repoId}`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const reindexDocs = async (repoId: number) => {
    try {
      await api.reindexDocs(repoId);
      await load();
      setMessage(`Reindexed docs for repo #${repoId}`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const reindexRepo = async (repoId: number) => {
    try {
      await api.reindexRepo(repoId);
      await load();
      setMessage(`Reindexed repo #${repoId}`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  return (
    <section>
      <h2>Repo Dashboard</h2>
      <button onClick={() => void load()}>Refresh</button>
      {message && <p role="status">{message}</p>}
      {repos.length === 0 ? (
        <p>No repos added yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Repo</th>
              <th>Last Sync</th>
              <th>Last Index</th>
              <th>Cached</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {repos.map((repo) => {
              const status = statuses[repo.id];
              return (
                <tr key={repo.id}>
                  <td>{repo.full_name}</td>
                  <td>{status?.last_sync_at || repo.last_sync_at || "—"}</td>
                  <td>{status?.last_index_at || repo.last_index_at || "—"}</td>
                  <td>
                    {status ? `${status.issues_cached} issues / ${status.prs_cached} PRs` : "—"}
                    {status?.last_error ? ` (error: ${status.last_error})` : ""}
                  </td>
                  <td style={{ display: "flex", gap: 6 }}>
                    <button onClick={() => void syncNow(repo.id)}>Sync now</button>
                    <button onClick={() => void reindexDocs(repo.id)}>Reindex docs</button>
                    <button onClick={() => void reindexRepo(repo.id)}>Reindex repo</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}
