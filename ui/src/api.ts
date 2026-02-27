export type PendingChangesetsResponse = {
  items: Array<{
    id: number;
    operation: string;
    repo: string;
    status: string;
  }>;
  summary: { count: number };
};

export type InboxItem = {
  source: "pm_bot" | "github";
  item_type: string;
  id: string;
  title: string;
  repo: string;
  url: string;
  state: string;
  priority: string;
  age_hours: number;
  action: "approve" | "review" | "triage";
  requires_internal_approval: boolean;
  stale: boolean;
  stale_reason: string;
  metadata: Record<string, unknown>;
};

export type UnifiedInboxResponse = {
  schema_version: "inbox/v1";
  items: InboxItem[];
  diagnostics: {
    cache: { hit: boolean; ttl_seconds: number; key: string };
    rate_limit: { remaining: number; reset_at: string; source: string };
    queries: {
      calls: number;
      chunk_size: number;
      chunks: Array<{ repo: string; labels: string[]; q: string }>;
    };
  };
  summary: {
    count: number;
    pm_bot_count: number;
    github_count: number;
  };
};

export type GraphTreeNode = {
  issue_ref: string;
  title: string;
  type: string;
  provenance?: string;
  children: GraphTreeNode[];
};

export type GraphTreeResponse = {
  root: GraphTreeNode;
  warnings: Array<{ code: string; message: string }>;
};

export type GraphDepsResponse = {
  nodes: Array<{ id: string; title: string; type: string; area: string }>;
  edges: Array<{ from: string; to: string; edge_type: string; provenance: string }>;
  warnings: Array<{ code: string; message: string }>;
  summary: { node_count: number; edge_count: number };
};

export type ContextPackResponse = {
  schema_version: string;
  profile: string;
  hash: string;
  budget: {
    max_chars: number;
    used_chars: number;
    strategy: string;
  };
  manifest: {
    included_segments: string[];
    excluded_segments: string[];
    exclusion_reasons: Record<string, number>;
    redaction_counts: { total: number; by_category: Record<string, number> };
  };
};

export type AgentRunRecord = {
  run_id: string;
  status: string;
  status_reason: string;
  created_by: string;
  intent: string;
  model: string;
  adapter_name: string;
  claimed_by: string;
  retry_count: number;
  max_retries: number;
  last_error: string;
  job_id: string;
  artifact_paths: string[];
};

export type AgentRunTransition = {
  run_id: string;
  from_status: string;
  to_status: string;
  reason_code: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AgentRunTransitionsResponse = {
  items: AgentRunTransition[];
  summary: { count: number };
};

export type AgentRunClaimResponse = {
  items: AgentRunRecord[];
  summary: { count: number };
};

export type AuditChainEvent = {
  id: number;
  event_type: string;
  payload: Record<string, unknown>;
  tenant_context: Record<string, unknown>;
  created_at: string;
};

export type AuditChainResponse = {
  schema_version: "audit_chain/v1";
  items: AuditChainEvent[];
  summary: {
    count: number;
    total: number;
    next_offset: number | null;
    filters: {
      run_id: string;
      event_type: string;
      repo: string;
      actor: string;
      start_at: string;
      end_at: string;
    };
  };
};

export type AuditRollupsResponse = {
  schema_version: "audit_rollups/v1";
  summary: {
    sample_size: number;
    completion_rate: number;
    retry_count: number;
    dead_letter_count: number;
    denial_count: number;
    average_queue_age_seconds: number;
  };
  top_reason_codes: Array<{ reason_code: string; count: number }>;
  repo_concentration: Array<{ repo: string; count: number }>;
};

export type AuditIncidentBundleResponse = {
  schema_version: "incident_bundle/v1";
  export: { run_id: string; actor: string; generated_at: string };
  runbook_hooks: Record<string, string>;
  chain: AuditChainResponse;
  rollups: AuditRollupsResponse;
};

export type ReportIrValidation = {
  errors: string[];
  warnings: string[];
};

export type ReportIrIntakeResponse = {
  draft_id: string;
  schema_version: "report_ir_draft/v1";
  draft: Record<string, unknown>;
  validation: ReportIrValidation;
};

export type ReportIrConfirmResponse = {
  status: "confirmed";
  confirmation_id: string;
  validation: ReportIrValidation;
  report_ir: Record<string, unknown>;
};

export type ReportIrPreviewItem = {
  repo: string;
  operation: string;
  item_type?: string;
  stable_id: string;
  target_ref: string;
  payload: Record<string, unknown>;
  idempotency_key: string;
};

export type ReportIrPreviewNode = {
  stable_id: string;
  title: string;
  item_type: string;
  parent_id: string;
  blocked_by: string[];
  depends_on: string[];
};

export type ReportIrPreviewEdge = {
  edge_type: "parent_child" | "blocked_by" | "depends_on";
  source: string;
  target: string;
  provenance: string;
};

export type ReportIrDependencyPreviewRepo = {
  repo: string;
  nodes: ReportIrPreviewNode[];
  edges: ReportIrPreviewEdge[];
};

export type ReportIrPreviewResponse = {
  schema_version: "changeset_preview/v1";
  items: ReportIrPreviewItem[];
  dependency_preview?: {
    repos: ReportIrDependencyPreviewRepo[];
  };
  summary: {
    count: number;
    repos: string[];
    repo_count: number;
  };
};

export type ReportIrProposalResponse = {
  schema_version: "report_ir_proposal/v1";
  items: Array<{
    stable_id: string;
    repo: string;
    idempotency_key: string;
    changeset: {
      id: number;
      operation: string;
      repo: string;
      payload: Record<string, unknown>;
      status: string;
      requested_by: string;
      approved_by: string;
      run_id: string;
      target_ref: string;
      idempotency_key: string;
      reason_code: string;
      created_at: string;
      updated_at: string;
    };
  }>;
  summary: { count: number };
};



export type OnboardingReadinessResponse = {
  readiness_state: string;
  updated_at: string;
};

export type RepoRegistryEntry = {
  id: number;
  workspace_id: number;
  full_name: string;
  default_branch: string;
  added_at: string;
  last_sync_at: string;
  last_index_at: string;
  last_error: string;
};

export type RepoSearchResult = {
  full_name: string;
  already_added: boolean;
};

export type RepoSyncStatusResponse = {
  repo_id: number;
  full_name: string;
  last_sync_at: string;
  last_index_at: string;
  last_error: string;
  issues_cached: number;
  prs_cached: number;
};

export class ApiError extends Error {
  readonly status: number;
  readonly reasonCode: string;

  constructor(message: string, status: number, reasonCode = "request_failed") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.reasonCode = reasonCode;
  }
}

const baseUrl = (import.meta.env.VITE_PM_BOT_API_BASE as string | undefined) ?? "http://127.0.0.1:8000";

async function httpJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const payload = await response.json();
  if (!response.ok) {
    const reasonCode = String(payload.reason_code ?? payload.error ?? "request_failed");
    throw new ApiError(String(payload.error ?? reasonCode), response.status, reasonCode);
  }
  return payload as T;
}

export function formatApiError(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.reasonCode}${error.message && error.message !== error.reasonCode ? ` (${error.message})` : ""}`;
  }
  return (error as Error).message;
}

export const api = {

  onboardingReadiness: () => httpJson<OnboardingReadinessResponse>("/onboarding/readiness"),
  onboardingDryRun: () =>
    httpJson<{ readiness_state: string; reason_code: string; checks: Record<string, boolean> }>("/onboarding/dry-run", {
      method: "POST",
      body: JSON.stringify({}),
    }),
  listRepos: () => httpJson<{ items: RepoRegistryEntry[]; summary: { count: number } }>("/repos"),
  searchRepos: (query: string) =>
    httpJson<{ items: RepoSearchResult[]; summary: { count: number } }>(`/repos/search?q=${encodeURIComponent(query)}`),
  addRepo: (params: { full_name: string; since_days?: number }) =>
    httpJson<RepoRegistryEntry>("/repos/add", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  syncRepo: (repoId: number) => httpJson<{ issues_upserted: number; prs_upserted: number }>(`/repos/${repoId}/sync`, { method: "POST" }),
  repoSyncStatus: (repoId: number) => httpJson<RepoSyncStatusResponse>(`/repos/${repoId}/status`),
  reindexDocs: (repoId = 0) =>
    httpJson<{ status: string; documents_indexed: number; chunks_upserted: number }>("/repos/reindex-docs", {
      method: "POST",
      body: JSON.stringify({ repo_id: repoId }),
    }),
  reindexRepo: (repoId: number) =>
    httpJson<{ status: string; documents_indexed: number; chunks_upserted: number }>(`/repos/${repoId}/reindex`, {
      method: "POST",
    }),
  pendingChangesets: () => httpJson<PendingChangesetsResponse>("/changesets/pending"),
  unifiedInbox: (params: { actor?: string; labels?: string[]; repos?: string[] } = {}) => {
    const q = new URLSearchParams();
    if (params.actor) q.set("actor", params.actor);
    if (params.labels && params.labels.length > 0) q.set("labels", params.labels.join(","));
    if (params.repos && params.repos.length > 0) q.set("repos", params.repos.join(","));
    const suffix = q.toString();
    return httpJson<UnifiedInboxResponse>(`/inbox${suffix ? `?${suffix}` : ""}`);
  },
  approveChangeset: (id: number, approvedBy: string) =>
    httpJson<{ status: string }>(`/changesets/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  graphTree: (root: string) => httpJson<GraphTreeResponse>(`/graph/tree?root=${encodeURIComponent(root)}`),
  graphDeps: () => httpJson<GraphDepsResponse>("/graph/deps"),
  contextPack: (params: {
    issue_ref: string;
    budget?: number;
    profile?: string;
    schema_version?: string;
    run_id?: string;
    requested_by?: string;
  }) => {
    const q = new URLSearchParams({ issue_ref: params.issue_ref });
    if (params.budget !== undefined) q.set("budget", String(params.budget));
    if (params.profile) q.set("profile", params.profile);
    if (params.schema_version) q.set("schema_version", params.schema_version);
    if (params.run_id) q.set("run_id", params.run_id);
    if (params.requested_by) q.set("requested_by", params.requested_by);
    return httpJson<ContextPackResponse>(`/context-pack?${q.toString()}`);
  },
  proposeAgentRun: (params: {
    created_by: string;
    spec: {
      run_id: string;
      model: string;
      intent: string;
      requires_approval: boolean;
      adapter: string;
      max_retries?: number;
    };
  }) =>
    httpJson<AgentRunRecord>("/agent-runs/propose", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  transitionAgentRun: (params: { run_id: string; to_status: string; reason_code: string; actor: string }) =>
    httpJson<AgentRunRecord>("/agent-runs/transition", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  claimAgentRuns: (params: { worker_id: string; limit?: number; lease_seconds?: number }) =>
    httpJson<AgentRunClaimResponse>("/agent-runs/claim", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  executeAgentRun: (params: { run_id: string; worker_id: string }) =>
    httpJson<AgentRunRecord>("/agent-runs/execute", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  cancelAgentRun: (params: { run_id: string; actor?: string }) =>
    httpJson<AgentRunRecord>("/agent-runs/cancel", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  agentRunTransitions: (run_id: string) =>
    httpJson<AgentRunTransitionsResponse>(`/agent-runs/transitions?run_id=${encodeURIComponent(run_id)}`),
  auditChain: (params: {
    run_id?: string;
    event_type?: string;
    repo?: string;
    actor?: string;
    start_at?: string;
    end_at?: string;
    limit?: number;
    offset?: number;
  } = {}) => {
    const q = new URLSearchParams();
    if (params.run_id) q.set("run_id", params.run_id);
    if (params.event_type) q.set("event_type", params.event_type);
    if (params.repo) q.set("repo", params.repo);
    if (params.actor) q.set("actor", params.actor);
    if (params.start_at) q.set("start_at", params.start_at);
    if (params.end_at) q.set("end_at", params.end_at);
    if (params.limit !== undefined) q.set("limit", String(params.limit));
    if (params.offset !== undefined) q.set("offset", String(params.offset));
    return httpJson<AuditChainResponse>(`/audit/chain${q.toString() ? `?${q.toString()}` : ""}`);
  },
  auditRollups: (params: { run_id?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.run_id) q.set("run_id", params.run_id);
    return httpJson<AuditRollupsResponse>(`/audit/rollups${q.toString() ? `?${q.toString()}` : ""}`);
  },
  auditIncidentBundle: (params: { run_id?: string; actor?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.run_id) q.set("run_id", params.run_id);
    if (params.actor) q.set("actor", params.actor);
    return httpJson<AuditIncidentBundleResponse>(`/audit/incident-bundle${q.toString() ? `?${q.toString()}` : ""}`);
  },
  reportIrIntake: (params: {
    natural_text: string;
    org: string;
    repos?: string[];
    run_id?: string;
    requested_by?: string;
    generated_at?: string;
  }) =>
    httpJson<ReportIrIntakeResponse>("/report-ir/intake", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  reportIrConfirm: (params: {
    report_ir: Record<string, unknown>;
    confirmed_by: string;
    run_id?: string;
    draft?: Record<string, unknown>;
  }) =>
    httpJson<ReportIrConfirmResponse>("/report-ir/confirm", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  reportIrPreview: (params: { report_ir: Record<string, unknown>; run_id?: string }) =>
    httpJson<ReportIrPreviewResponse>("/report-ir/preview", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  reportIrPropose: (params: { report_ir: Record<string, unknown>; run_id: string; requested_by: string }) =>
    httpJson<ReportIrProposalResponse>("/report-ir/propose", {
      method: "POST",
      body: JSON.stringify(params),
    }),
};
