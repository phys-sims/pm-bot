export type PendingChangesetsResponse = {
  items: Array<{
    id: number;
    operation: string;
    repo: string;
    status: string;
  }>;
  summary: { count: number };
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
  approveChangeset: (id: number, approvedBy: string) =>
    httpJson<{ status: string }>(`/changesets/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  graphTree: (root: string) =>
    httpJson<GraphTreeResponse>(`/graph/tree?root=${encodeURIComponent(root)}`),
  graphDeps: () => httpJson<GraphDepsResponse>("/graph/deps"),
};
