import { useEffect, useState } from "react";
import { api } from "./api";

export function InboxPage() {
  const [pending, setPending] = useState<Array<{ id: number; operation: string; repo: string }>>([]);
  const [message, setMessage] = useState("");

  const load = async () => {
    try {
      const response = await api.pendingChangesets();
      setPending(response.items);
      setMessage("");
    } catch (error) {
      setMessage(`Error: ${(error as Error).message}`);
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
      setMessage(`Error: ${(error as Error).message}`);
    }
  };

  return (
    <section>
      <h2>Approval Inbox</h2>
      <p>Pending: {pending.length}</p>
      {message && <div role="status">{message}</div>}
      {pending.length === 0 ? (
        <p>No pending changesets.</p>
      ) : (
        <ul>
          {pending.map((item) => (
            <li key={item.id}>
              <strong>#{item.id}</strong> {item.operation} on {item.repo}{" "}
              <button onClick={() => void approve(item.id)}>Approve</button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
