import { useState } from "react";
import { AgentRunsPage } from "./AgentRunsPage";
import { AuditOpsPage } from "./AuditOpsPage";
import { ContextPackPage } from "./ContextPackPage";
import { InboxPage } from "./InboxPage";
import { PlanIntakePage } from "./PlanIntakePage";
import { TreePage } from "./TreePage";
import { OnboardingPage } from "./OnboardingPage";
import { RepoDashboardPage } from "./RepoDashboardPage";

type RouteKey = "onboarding" | "repos" | "inbox" | "tree" | "agentRuns" | "contextPack" | "auditOps" | "planIntake";

type RouteConfig = {
  key: RouteKey;
  label: string;
  render: () => JSX.Element;
};

const ROUTES: RouteConfig[] = [
  { key: "onboarding", label: "Onboarding", render: () => <OnboardingPage /> },
  { key: "repos", label: "Repo Dashboard", render: () => <RepoDashboardPage /> },
  { key: "inbox", label: "Inbox", render: () => <InboxPage /> },
  { key: "tree", label: "Tree", render: () => <TreePage /> },
  { key: "agentRuns", label: "Agent Runs", render: () => <AgentRunsPage /> },
  { key: "contextPack", label: "Context Pack", render: () => <ContextPackPage /> },
  { key: "auditOps", label: "Audit Ops", render: () => <AuditOpsPage /> },
  { key: "planIntake", label: "Plan Intake", render: () => <PlanIntakePage /> },
];

export function App() {
  const [route, setRoute] = useState<RouteKey>("inbox");
  const activeRoute = ROUTES.find((item) => item.key === route) ?? ROUTES[0];

  return (
    <main style={{ fontFamily: "sans-serif", maxWidth: 1000, margin: "0 auto", padding: 16 }}>
      <h1>pm-bot UI MVP</h1>
      <nav style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {ROUTES.map((item) => (
          <button key={item.key} aria-current={item.key === activeRoute.key ? "page" : undefined} onClick={() => setRoute(item.key)}>
            {item.label}
          </button>
        ))}
      </nav>
      {activeRoute.render()}
    </main>
  );
}
