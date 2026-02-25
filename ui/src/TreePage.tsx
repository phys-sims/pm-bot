import { useState } from "react";
import { api, formatApiError, GraphTreeNode } from "./api";

function TreeNode({ node }: { node: GraphTreeNode }) {
  return (
    <li>
      {node.title || node.issue_ref} <em>[{node.provenance ?? "sub_issue"}]</em>
      {node.children.length > 0 && (
        <ul>
          {node.children.map((child) => (
            <TreeNode key={child.issue_ref} node={child} />
          ))}
        </ul>
      )}
    </li>
  );
}

export function TreePage() {
  const [rootRef, setRootRef] = useState("draft:epic:root");
  const [tree, setTree] = useState<GraphTreeNode | null>(null);
  const [warnings, setWarnings] = useState<Array<{ code: string; message: string }>>([]);
  const [depSummary, setDepSummary] = useState<{ node_count: number; edge_count: number } | null>(null);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [treeResponse, depsResponse] = await Promise.all([api.graphTree(rootRef), api.graphDeps()]);
      setTree(treeResponse.root);
      setWarnings(treeResponse.warnings.concat(depsResponse.warnings));
      setDepSummary(depsResponse.summary);
      setError("");
    } catch (err) {
      setError(formatApiError(err));
    }
  };

  return (
    <section>
      <h2>Tree and Dependencies</h2>
      <label>
        Root ref:
        <input value={rootRef} onChange={(event) => setRootRef(event.target.value)} />
      </label>
      <button onClick={() => void load()}>Load graph</button>
      {error && <p role="alert">Error: {error}</p>}
      {depSummary && <p>Dependency summary: {depSummary.node_count} nodes / {depSummary.edge_count} edges</p>}
      {warnings.length > 0 && (
        <aside>
          <h3>Warnings</h3>
          <ul>
            {warnings.map((warning) => (
              <li key={`${warning.code}:${warning.message}`}>{warning.code}: {warning.message}</li>
            ))}
          </ul>
        </aside>
      )}
      {tree && (
        <ul>
          <TreeNode node={tree} />
        </ul>
      )}
    </section>
  );
}
