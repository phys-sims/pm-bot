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

const baseUrl = (import.meta.env.VITE_PM_BOT_API_BASE as string | undefined) ?? "http://127.0.0.1:8000";

async function httpJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.reason_code ?? payload.error ?? "request_failed");
  }
  return payload as T;
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
  graphTree: (root: string) =>
    httpJson<GraphTreeResponse>(`/graph/tree?root=${encodeURIComponent(root)}`),
  graphDeps: () => httpJson<GraphDepsResponse>("/graph/deps"),
};
