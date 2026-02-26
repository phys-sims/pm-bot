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

  const repos = useMemo(
    () => reposRaw.split(",").map((repo) => repo.trim()).filter(Boolean),
    [reposRaw],
  );

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
        <button disabled={!previewResponse} onClick={() => void proposeChangesets()}>
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
