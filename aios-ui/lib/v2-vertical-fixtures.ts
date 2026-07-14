import fixtureDocument from "@/fixtures/v2-vertical-slice-fixtures.json";

export type V2FixtureState = "healthy" | "empty" | "blocked" | "failed" | "needs_review" | "closed";

export type V2FixtureEvidence = {
  id: string;
  kind: "check" | "receipt" | "artifact";
  source: string;
  status: "verified" | "pending" | "failed";
  summary: string;
};

export type V2FixtureApproval = {
  id: string;
  kind: "truth-writeback";
  state: "not_required" | "pending" | "approved" | "rejected";
  target: string;
  actor: string;
  reason: string;
};

export type V2VerticalFixture = {
  id: string;
  state: V2FixtureState;
  objective: string;
  route: {
    id: string;
    project_id: string | null;
    task_family: string;
    workflow_key: string;
    status: "ready" | "blocked";
    authority: "python-control-plane";
    rationale: string;
  };
  packet: {
    id: string;
    source_refs: string[];
    omitted_refs: string[];
    freshness: "current" | "stale";
    selection_status: "complete" | "partial" | "blocked";
  };
  run: {
    id: string;
    status: "planned" | "ready" | "in_progress" | "failed" | "completed";
    stage: "start-work" | "verify" | "gated-review" | "closeout";
    evidence_ids: string[];
    approval_ids: string[];
    next_action_id: string | null;
  };
  evidence: V2FixtureEvidence[];
  approvals: V2FixtureApproval[];
  projection: {
    mode: "start-work" | "verify" | "gated-review" | "closeout";
    title: string;
    state_label: string;
    next_action: string | null;
    drill_down_path: string;
  };
};

export type V2VerticalFixtureDocument = {
  schema_version: "aios-v2-vertical-fixtures-v0.1";
  owner: "python-control-plane";
  fixtures: V2VerticalFixture[];
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === "object" && !Array.isArray(value);

const isOneOf = <T extends string>(value: unknown, allowed: readonly T[]): value is T =>
  typeof value === "string" && allowed.includes(value as T);

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === "string");

const isEvidence = (value: unknown): value is V2FixtureEvidence => {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.id === "string" &&
    isOneOf(value.kind, ["check", "receipt", "artifact"] as const) &&
    typeof value.source === "string" &&
    isOneOf(value.status, ["verified", "pending", "failed"] as const) &&
    typeof value.summary === "string"
  );
};

const isApproval = (value: unknown): value is V2FixtureApproval => {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.id === "string" &&
    value.kind === "truth-writeback" &&
    isOneOf(value.state, ["not_required", "pending", "approved", "rejected"] as const) &&
    typeof value.target === "string" &&
    typeof value.actor === "string" &&
    typeof value.reason === "string"
  );
};

const isFixture = (value: unknown): value is V2VerticalFixture => {
  if (!isRecord(value) || !isRecord(value.route) || !isRecord(value.packet) || !isRecord(value.run) || !isRecord(value.projection)) {
    return false;
  }
  const route = value.route;
  const packet = value.packet;
  const run = value.run;
  const projection = value.projection;
  return (
    typeof value.id === "string" &&
    isOneOf(value.state, ["healthy", "empty", "blocked", "failed", "needs_review", "closed"] as const) &&
    typeof value.objective === "string" &&
    typeof route.id === "string" &&
    (typeof route.project_id === "string" || route.project_id === null) &&
    typeof route.task_family === "string" &&
    typeof route.workflow_key === "string" &&
    isOneOf(route.status, ["ready", "blocked"] as const) &&
    route.authority === "python-control-plane" &&
    typeof route.rationale === "string" &&
    typeof packet.id === "string" &&
    isStringArray(packet.source_refs) &&
    isStringArray(packet.omitted_refs) &&
    isOneOf(packet.freshness, ["current", "stale"] as const) &&
    isOneOf(packet.selection_status, ["complete", "partial", "blocked"] as const) &&
    typeof run.id === "string" &&
    isOneOf(run.status, ["planned", "ready", "in_progress", "failed", "completed"] as const) &&
    isOneOf(run.stage, ["start-work", "verify", "gated-review", "closeout"] as const) &&
    isStringArray(run.evidence_ids) &&
    isStringArray(run.approval_ids) &&
    (typeof run.next_action_id === "string" || run.next_action_id === null) &&
    Array.isArray(value.evidence) &&
    value.evidence.every(isEvidence) &&
    Array.isArray(value.approvals) &&
    value.approvals.every(isApproval) &&
    isOneOf(projection.mode, ["start-work", "verify", "gated-review", "closeout"] as const) &&
    typeof projection.title === "string" &&
    typeof projection.state_label === "string" &&
    (typeof projection.next_action === "string" || projection.next_action === null) &&
    typeof projection.drill_down_path === "string"
  );
};

const isFixtureDocument = (value: unknown): value is V2VerticalFixtureDocument =>
  isRecord(value) &&
  value.schema_version === "aios-v2-vertical-fixtures-v0.1" &&
  value.owner === "python-control-plane" &&
  Array.isArray(value.fixtures) &&
  value.fixtures.every(isFixture);

if (!isFixtureDocument(fixtureDocument)) {
  throw new Error("Invalid AIOS v2 vertical fixture document.");
}

export const v2VerticalFixtureDocument: V2VerticalFixtureDocument = fixtureDocument;
