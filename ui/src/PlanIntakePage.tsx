import { useMemo, useState } from "react";
import {
  api,
  formatApiError,
  type ReportIrConfirmResponse,
  type ReportIrIntakeResponse,
  type ReportIrPreviewResponse,
  type ReportIrProposalResponse,
} from "./api";

type Step = 1 | 2 | 3 | 4 | 5 | 6;

function prettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

export function PlanIntakePage() {
  const [naturalText, setNaturalText] = useState("- Create backend route tests\n- Add UI page\n- Validate release notes");
  const [org, setOrg] = useState("phys-sims");
  const [reposRaw, setReposRaw] = useState("phys-sims/pm-bot");
  const [runId, setRunId] = useState("run-ui-plan-intake");
  const [requestedBy, setRequestedBy] = useState("ui-operator");

  const [draftResponse, setDraftResponse] = useState<ReportIrIntakeResponse | null>(null);
  const [reportIrText, setReportIrText] = useState("");
  const [confirmResponse, setConfirmResponse] = useState<ReportIrConfirmResponse | null>(null);
  const [previewResponse, setPreviewResponse] = useState<ReportIrPreviewResponse | null>(null);
  const [proposalResponse, setProposalResponse] = useState<ReportIrProposalResponse | null>(null);
  const [message, setMessage] = useState("");

  const repos = useMemo(() => reposRaw.split(",").map((repo) => repo.trim()).filter(Boolean), [reposRaw]);

  const parsedReportIr = useMemo<Record<string, unknown> | null>(() => {
    if (!reportIrText.trim()) {
      return null;
    }
    try {
      const parsed = JSON.parse(reportIrText);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        return null;
      }
      return parsed as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [reportIrText]);

  const currentStep: Step = proposalResponse
    ? 6
    : previewResponse
      ? 5
      : confirmResponse
        ? 4
        : parsedReportIr
          ? 3
          : draftResponse
            ? 2
            : 1;

  const groupedPreview = useMemo(() => {
    const grouped: Record<string, Record<string, number>> = {};
    for (const item of previewResponse?.items ?? []) {
      if (!grouped[item.repo]) {
        grouped[item.repo] = {};
      }
      grouped[item.repo][item.operation] = (grouped[item.repo][item.operation] ?? 0) + 1;
    }
    return grouped;
  }, [previewResponse]);

  const previewValidation = useMemo(() => {
    if (!parsedReportIr || !previewResponse) {
      return null;
    }
    const report = typeof parsedReportIr.report === "object" && parsedReportIr.report ? parsedReportIr.report : {};
    const scope = typeof (report as { scope?: unknown }).scope === "object" && (report as { scope?: unknown }).scope
      ? ((report as { scope?: unknown }).scope as { org?: unknown; repos?: unknown })
      : {};
    const defaultRepo =
      Array.isArray(scope.repos) && scope.repos.length > 0
        ? String(scope.repos[0] ?? "").trim()
        : `${String(scope.org ?? "").trim()}/pm-bot`;

    const nodes = previewResponse.dependency_preview?.repos.flatMap((repoGroup) =>
      repoGroup.nodes.map((node) => ({ ...node, repo: repoGroup.repo })),
    ) ?? [];
    const nodeIds = new Set(nodes.map((node) => node.stable_id));

    const errors: string[] = [];
    const warnings: string[] = [];

    for (const node of nodes) {
      if (node.parent_id && !nodeIds.has(node.parent_id)) {
        errors.push(`${node.stable_id} references missing parent ${node.parent_id}`);
      }
      for (const blockerId of node.blocked_by ?? []) {
        if (!nodeIds.has(blockerId)) {
          warnings.push(`${node.stable_id} blocked_by ${blockerId} is external or unresolved`);
        }
      }
    }

    if (nodes.length === 0 && previewResponse.summary.count > 0) {
      warnings.push("Preview returned operations but no dependency graph metadata.");
    }

    if (nodes.some((node) => !node.repo)) {
      warnings.push(`Some nodes are missing repo metadata; default repo ${defaultRepo || "<missing>"} assumed.`);
    }

    return { errors: Array.from(new Set(errors)).sort(), warnings: Array.from(new Set(warnings)).sort() };
  }, [parsedReportIr, previewResponse]);

  const canPropose = Boolean(previewResponse) && (previewValidation?.errors.length ?? 0) === 0;

  const submitIntake = async () => {
    try {
      const response = await api.reportIrIntake({
        natural_text: naturalText,
        org,
        repos,
        run_id: runId,
        requested_by: requestedBy,
      });
      setDraftResponse(response);
      setReportIrText(prettyJson(response.draft));
      setConfirmResponse(null);
      setPreviewResponse(null);
      setProposalResponse(null);
      setMessage(`Draft generated: ${response.draft_id}`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const confirmReportIr = async () => {
    if (!parsedReportIr) {
      setMessage("Error: report_ir JSON must be a valid object.");
      return;
    }
    try {
      const response = await api.reportIrConfirm({
        report_ir: parsedReportIr,
        confirmed_by: requestedBy,
        run_id: runId,
        draft: draftResponse?.draft,
      });
      setConfirmResponse(response);
      setPreviewResponse(null);
      setProposalResponse(null);
      setMessage(`ReportIR confirmed: ${response.confirmation_id}`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const previewChangesets = async () => {
    if (!parsedReportIr) {
      setMessage("Error: report_ir JSON must be a valid object.");
      return;
    }
    try {
      const response = await api.reportIrPreview({ report_ir: parsedReportIr, run_id: runId });
      setPreviewResponse(response);
      setProposalResponse(null);
      setMessage(`Preview generated for ${response.summary.count} operations.`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  const proposeChangesets = async () => {
    if (!parsedReportIr) {
      setMessage("Error: report_ir JSON must be a valid object.");
      return;
    }
    if (!canPropose) {
      setMessage("Error: resolve preview validation errors before proposing changesets.");
      return;
    }
    try {
      const response = await api.reportIrPropose({
        report_ir: parsedReportIr,
        run_id: runId,
        requested_by: requestedBy,
      });
      setProposalResponse(response);
      setMessage(`Proposed ${response.summary.count} approval-gated changesets.`);
    } catch (error) {
      setMessage(`Error: ${formatApiError(error)}`);
    }
  };

  return (
    <section>
      <h2>Plan Intake</h2>
      <p>Guided ReportIR stepper from natural text intake through approval-gated changeset proposal.</p>
      <ol>
        <li aria-current={currentStep === 1 ? "step" : undefined}>Input plan text and request metadata</li>
        <li aria-current={currentStep === 2 ? "step" : undefined}>Generate draft via /report-ir/intake</li>
        <li aria-current={currentStep === 3 ? "step" : undefined}>Edit draft report_ir JSON</li>
        <li aria-current={currentStep === 4 ? "step" : undefined}>Confirm report_ir via /report-ir/confirm</li>
        <li aria-current={currentStep === 5 ? "step" : undefined}>Preview grouped operations via /report-ir/preview</li>
        <li aria-current={currentStep === 6 ? "step" : undefined}>Propose approval-gated changesets via /report-ir/propose</li>
      </ol>

      <div style={{ display: "grid", gap: 8, maxWidth: 760 }}>
        <label>
          Plan text / markdown:
          <textarea rows={6} value={naturalText} onChange={(event) => setNaturalText(event.target.value)} />
        </label>
        <label>
          Org:
          <input value={org} onChange={(event) => setOrg(event.target.value)} />
        </label>
        <label>
          Repos (comma-separated):
          <input value={reposRaw} onChange={(event) => setReposRaw(event.target.value)} />
        </label>
        <label>
          Run ID:
          <input value={runId} onChange={(event) => setRunId(event.target.value)} />
        </label>
        <label>
          Requested by:
          <input value={requestedBy} onChange={(event) => setRequestedBy(event.target.value)} />
        </label>
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
        <button onClick={() => void submitIntake()}>1-2) Draft from intake</button>
        <button disabled={!reportIrText.trim()} onClick={() => void confirmReportIr()}>
          4) Confirm report_ir
        </button>
        <button disabled={!confirmResponse} onClick={() => void previewChangesets()}>
          5) Preview operations
        </button>
        <button disabled={!canPropose} onClick={() => void proposeChangesets()}>
          6) Propose changesets
        </button>
      </div>

      <h3>Editable report_ir JSON</h3>
      <textarea
        aria-label="Editable report_ir JSON"
        rows={16}
        style={{ width: "100%" }}
        value={reportIrText}
        onChange={(event) => setReportIrText(event.target.value)}
      />

      {message && <p role="status">{message}</p>}

      {draftResponse && (
        <article>
          <h3>Draft validation</h3>
          <p>Errors: {draftResponse.validation.errors.length}</p>
          <p>Warnings: {draftResponse.validation.warnings.length}</p>
        </article>
      )}

      {previewValidation && (previewValidation.errors.length > 0 || previewValidation.warnings.length > 0) && (
        <article>
          <h3>Preview validation</h3>
          {previewValidation.errors.length > 0 && (
            <>
              <p style={{ color: "#8b0000", fontWeight: 700 }}>Errors ({previewValidation.errors.length})</p>
              <ul>
                {previewValidation.errors.map((error) => (
                  <li key={error}>{error}</li>
                ))}
              </ul>
            </>
          )}
          {previewValidation.warnings.length > 0 && (
            <>
              <p style={{ color: "#7a5200", fontWeight: 700 }}>Warnings ({previewValidation.warnings.length})</p>
              <ul>
                {previewValidation.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </>
          )}
        </article>
      )}

      {previewResponse && (
        <article>
          <h3>Grouped proposed operations</h3>
          <ul>
            {Object.entries(groupedPreview).map(([repo, operations]) => (
              <li key={repo}>
                <strong>{repo}</strong>
                <ul>
                  {Object.entries(operations).map(([operation, count]) => (
                    <li key={`${repo}-${operation}`}>
                      {operation}: {count}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
          <h3>Dependency preview by repo</h3>
          <ul>
            {(previewResponse.dependency_preview?.repos ?? []).map((repoGroup) => {
              const childrenByParent: Record<string, string[]> = {};
              for (const edge of repoGroup.edges) {
                if (edge.edge_type !== "parent_child") {
                  continue;
                }
                if (!childrenByParent[edge.source]) {
                  childrenByParent[edge.source] = [];
                }
                childrenByParent[edge.source].push(edge.target);
              }
              const nodeById = Object.fromEntries(repoGroup.nodes.map((node) => [node.stable_id, node]));
              const childSet = new Set(repoGroup.edges.filter((edge) => edge.edge_type === "parent_child").map((edge) => edge.target));
              const roots = repoGroup.nodes
                .map((node) => node.stable_id)
                .filter((stableId) => !childSet.has(stableId))
                .sort();

              const renderTree = (stableId: string, depth = 0): JSX.Element | null => {
                const node = nodeById[stableId];
                if (!node) {
                  return null;
                }
                const blockers = repoGroup.edges.filter(
                  (edge) => edge.edge_type === "blocked_by" && edge.source === stableId,
                );
                return (
                  <li key={`${stableId}-${depth}`}>
                    <span>
                      {node.item_type}: {node.title} ({node.stable_id})
                    </span>
                    {blockers.length > 0 && (
                      <ul>
                        {blockers.map((edge) => (
                          <li key={`${edge.source}-${edge.target}-blocked`}>blocked by {edge.target}</li>
                        ))}
                      </ul>
                    )}
                    {(childrenByParent[stableId] ?? []).length > 0 && (
                      <ul>{(childrenByParent[stableId] ?? []).sort().map((childId) => renderTree(childId, depth + 1))}</ul>
                    )}
                  </li>
                );
              };

              return (
                <li key={`preview-${repoGroup.repo}`}>
                  <strong>{repoGroup.repo}</strong>
                  <ul>{roots.map((rootId) => renderTree(rootId))}</ul>
                </li>
              );
            })}
          </ul>
          <p>Total operations: {previewResponse.summary.count}</p>
        </article>
      )}

      {proposalResponse && (
        <article>
          <h3>Proposal result</h3>
          <p>Created changesets: {proposalResponse.summary.count}</p>
        </article>
      )}
    </section>
  );
}
