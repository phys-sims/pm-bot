import { useEffect, useMemo, useState } from "react";
import { api, formatApiError, type RepoSearchResult } from "./api";

type ProgressStep = "token" | "repos" | "sync";

export function OnboardingPage() {
  const [tokenInput, setTokenInput] = useState("");
  const [tokenMode, setTokenMode] = useState<"env" | "manual">("env");
  const [query, setQuery] = useState("phys-sims");
  const [results, setResults] = useState<RepoSearchResult[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [message, setMessage] = useState("");
  const [syncLog, setSyncLog] = useState<string[]>([]);
  const [step, setStep] = useState<ProgressStep>("token");

  useEffect(() => {
    void searchRepos();
  }, []);

  const canContinueToken = tokenMode === "env" || tokenInput.trim().length > 0;

  const progress = useMemo(() => {
    if (step === "token") return "1/3";
    if (step === "repos") return "2/3";
    return "3/3";
  }, [step]);

  const searchRepos = async () => {
    try {
      const response = await api.searchRepos(query);
      setResults(response.items);
      if (!selectedRepo && response.items.length > 0) {
        const first = response.items.find((item) => !item.already_added) ?? response.items[0];
        setSelectedRepo(first.full_name);
      }
      setMessage("");
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const continueFromToken = () => {
    if (!canContinueToken) {
      setMessage("Set a token or choose env token mode.");
      return;
    }
    setStep("repos");
    setMessage(tokenMode === "env" ? "Using PM_BOT_GITHUB_* env token(s)." : "Token saved in browser session for this flow.");
  };

  const addAndSync = async () => {
    if (!selectedRepo) {
      setMessage("Select a repo first.");
      return;
    }
    try {
      setStep("sync");
      setSyncLog([`Adding ${selectedRepo}...`]);
      const added = await api.addRepo({ full_name: selectedRepo, since_days: 30 });
      setSyncLog((prev) => [...prev, `Added repo #${added.id}. Triggering sync...`]);
      const sync = await api.syncRepo(added.id);
      setSyncLog((prev) => [...prev, `Sync complete: ${sync.issues_upserted} issues, ${sync.prs_upserted} PRs.`]);
      const status = await api.repoSyncStatus(added.id);
      setSyncLog((prev) => [...prev, `Cache status: ${status.issues_cached} issues, ${status.prs_cached} PRs.`]);
      setMessage("Onboarding complete. Open Repo Dashboard for ongoing sync/reindex actions.");
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  return (
    <section>
      <h2>Onboarding Wizard</h2>
      <p>Progress: {progress}</p>
      <ol>
        <li aria-current={step === "token" ? "step" : undefined}>Set GitHub token mode</li>
        <li aria-current={step === "repos" ? "step" : undefined}>Search + select repo</li>
        <li aria-current={step === "sync" ? "step" : undefined}>Initial sync + status</li>
      </ol>

      <h3>1) GitHub token</h3>
      <label>
        <input type="radio" checked={tokenMode === "env"} onChange={() => setTokenMode("env")} /> Use env token (PM_BOT_GITHUB_READ_TOKEN / PM_BOT_GITHUB_WRITE_TOKEN)
      </label>
      <br />
      <label>
        <input type="radio" checked={tokenMode === "manual"} onChange={() => setTokenMode("manual")} /> Paste token (session-only helper)
      </label>
      {tokenMode === "manual" && (
        <div>
          <input type="password" value={tokenInput} onChange={(event) => setTokenInput(event.target.value)} placeholder="ghp_..." />
        </div>
      )}
      <div style={{ marginTop: 8 }}>
        <button onClick={continueFromToken}>Continue to repo selection</button>
      </div>

      {step !== "token" && (
        <>
          <h3>2) Add repositories</h3>
          <div style={{ display: "flex", gap: 8 }}>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="org/name" />
            <button onClick={() => void searchRepos()}>Search</button>
          </div>
          <ul>
            {results.map((item) => (
              <li key={item.full_name}>
                <label>
                  <input type="radio" name="repo-select" value={item.full_name} checked={selectedRepo === item.full_name} onChange={() => setSelectedRepo(item.full_name)} />
                  {item.full_name} {item.already_added ? "(already added)" : ""}
                </label>
              </li>
            ))}
          </ul>
          <button onClick={() => void addAndSync()}>Add + initial sync</button>
        </>
      )}

      {syncLog.length > 0 && (
        <article>
          <h3>3) Sync progress</h3>
          <ul>
            {syncLog.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </article>
      )}

      {message && <p role="status">{message}</p>}
    </section>
  );
}
