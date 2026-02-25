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
};

export type AgentRunClaimResponse = {
  items: AgentRunRecord[];
  summary: { count: number };
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
};
