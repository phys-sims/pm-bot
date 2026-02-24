import { useState } from "react";
import { InboxPage } from "./InboxPage";
import { TreePage } from "./TreePage";

export function App() {
  const [route, setRoute] = useState<"inbox" | "tree">("inbox");

  return (
    <main style={{ fontFamily: "sans-serif", maxWidth: 1000, margin: "0 auto", padding: 16 }}>
      <h1>pm-bot UI MVP</h1>
      <nav style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button onClick={() => setRoute("inbox")}>Inbox</button>
        <button onClick={() => setRoute("tree")}>Tree</button>
      </nav>
      {route === "inbox" ? <InboxPage /> : <TreePage />}
    </main>
  );
}
