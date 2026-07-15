import Database from "better-sqlite3";
import { existsSync, mkdirSync, readFileSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import type { FullConfig } from "@playwright/test";

export const M6_REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const testResultsDirectory = path.join(M6_REPO_ROOT, "aios-ui", "test-results");
export const M6_DATABASE_PATH = path.join(testResultsDirectory, "m6-verify-review-closeout.sqlite");

export const M6_FIXTURE_IDS = {
  project: "m6-browser-project",
  verifySession: "m6-session-verify",
  reviewSession: "m6-session-review",
  closeoutSession: "m6-session-closeout",
  verifyRun: "m6-run-verify",
  reviewRun: "m6-run-review",
  closeoutRun: "m6-run-closeout",
  verifyPacket: "m6-packet-verify",
  reviewPacket: "m6-packet-review",
  closeoutPacket: "m6-packet-closeout",
  closeoutArtifact: "m6-artifact-closeout",
} as const;

const timestamps = {
  verify: "2026-07-15T12:00:00.000Z",
  review: "2026-07-15T12:01:00.000Z",
  closeout: "2026-07-15T12:02:00.000Z",
} as const;

const structuredSections = (journey: string, touchedFile: string): string =>
  JSON.stringify([
    {
      title: "Task scope",
      items: [`M6 ${journey} journey is seeded for browser inspection.`],
    },
    {
      title: "Evidence",
      items: ["m6-evidence-browser-contract", touchedFile],
    },
    {
      title: "Closeout",
      items: ["Review lifecycle evidence and preserve file provenance."],
    },
  ]);

const removePriorDatabase = (): void => {
  for (const suffix of ["", "-wal", "-shm"]) {
    rmSync(`${M6_DATABASE_PATH}${suffix}`, { force: true });
  }
};

const seedDatabase = (): void => {
  mkdirSync(testResultsDirectory, { recursive: true });
  removePriorDatabase();

  const db = new Database(M6_DATABASE_PATH);
  db.pragma("foreign_keys = ON");
  db.exec(`
    CREATE TABLE schema_migrations (
      version INTEGER PRIMARY KEY,
      migration_id TEXT NOT NULL UNIQUE,
      checksum TEXT NOT NULL,
      applied_at TEXT NOT NULL,
      tool_version TEXT NOT NULL,
      pre_backup_ref TEXT,
      post_backup_ref TEXT
    );
    INSERT INTO schema_migrations (version, migration_id, checksum, applied_at, tool_version)
    VALUES (1, 'm6-browser-fixture', 'm6-browser-fixture', '2026-07-15T12:00:00.000Z', 'm6-browser-fixture');
  `);
  db.pragma("user_version = 1");
  db.exec(readFileSync(path.join(M6_REPO_ROOT, "schema.sql"), "utf8"));

  const seed = db.transaction(() => {
    const ids = M6_FIXTURE_IDS;
    const projectPath = path.join(M6_REPO_ROOT, "aios-ui");
    db.prepare(
      `INSERT INTO projects (id, name, repo_path, obsidian_path, status, created_at, updated_at)
       VALUES (?, ?, ?, ?, 'active', ?, ?)`,
    ).run(ids.project, "M6 Browser Contract", projectPath, path.join(M6_REPO_ROOT, ".m6-browser-obsidian"), timestamps.verify, timestamps.closeout);

    const insertSession = db.prepare(
      `INSERT INTO sessions (id, project_id, tool, started_at, ended_at, objective, status, cwd)
       VALUES (?, ?, 'codex', ?, ?, ?, ?, ?)`,
    );
    insertSession.run(ids.verifySession, ids.project, timestamps.verify, null, "Verify the browser contract", "open", projectPath);
    insertSession.run(ids.reviewSession, ids.project, timestamps.review, null, "Review the browser contract", "open", projectPath);
    insertSession.run(ids.closeoutSession, ids.project, timestamps.closeout, "2026-07-15T12:03:00.000Z", "Close out the browser contract", "closed", projectPath);

    const insertRun = db.prepare(
      `INSERT INTO orchestration_runs
        (id, project_id, session_id, objective, workflow_key, agent_key, status, rationale,
         assumptions_json, context_trace_json, backend_key, route_id, route_status,
         route_result_json, status_reason_json, packet_id, started_at, completed_at, created_at, updated_at)
       VALUES (?, ?, ?, ?, 'implementation-delivery', 'implementation-lead', ?, ?, '[]', '[]',
         'codex-managed-runtime', ?, 'ready', '{}', ?, ?, ?, ?, ?, ?)`,
    );
    insertRun.run(
      ids.verifyRun,
      ids.project,
      ids.verifySession,
      "Verify the Verify → Review → Closeout browser contract",
      "in_progress",
      "Verification evidence is being inspected.",
      "m6-route-verify",
      "{}",
      ids.verifyPacket,
      timestamps.verify,
      null,
      timestamps.verify,
      timestamps.verify,
    );
    insertRun.run(
      ids.reviewRun,
      ids.project,
      ids.reviewSession,
      "Review the Verify → Review → Closeout browser contract",
      "canceled",
      "Human review is required before closeout.",
      "m6-route-review",
      "{}",
      ids.reviewPacket,
      null,
      null,
      timestamps.review,
      timestamps.review,
    );
    insertRun.run(
      ids.closeoutRun,
      ids.project,
      ids.closeoutSession,
      "Close out the Verify → Review → Closeout browser contract",
      "completed",
      "Closeout evidence is durable and linked to the closed session.",
      "m6-route-closeout",
      "{}",
      ids.closeoutPacket,
      timestamps.closeout,
      "2026-07-15T12:03:00.000Z",
      timestamps.closeout,
      timestamps.closeout,
    );

    const insertPacket = db.prepare(
      `INSERT INTO briefing_packets
        (id, run_id, project_id, objective, workflow_key, agent_key, packet_markdown,
         sections_json, policy_mode, token_budget, route_id, route_result_json,
         selection_trace_json, omitted_context_json, created_at)
       VALUES (?, ?, ?, ?, 'implementation-delivery', 'implementation-lead', ?, ?,
         'compact-ranked', 900, ?, '{}', '[]', '[]', ?)`,
    );
    const packetMarkdown = "# M6 Browser Contract\n\nStructured packet sections for run inspection.";
    insertPacket.run(
      ids.verifyPacket,
      ids.verifyRun,
      ids.project,
      "Verify the Verify → Review → Closeout browser contract",
      packetMarkdown,
      structuredSections("Verify", "aios-ui/tests/browser/m6-verify-review-closeout.spec.ts"),
      "m6-route-verify",
      timestamps.verify,
    );
    insertPacket.run(
      ids.reviewPacket,
      ids.reviewRun,
      ids.project,
      "Review the Verify → Review → Closeout browser contract",
      packetMarkdown,
      structuredSections("Review", "aios-ui/tests/browser/m6-verify-review-closeout.spec.ts"),
      "m6-route-review",
      timestamps.review,
    );
    insertPacket.run(
      ids.closeoutPacket,
      ids.closeoutRun,
      ids.project,
      "Close out the Verify → Review → Closeout browser contract",
      packetMarkdown,
      structuredSections("Closeout", "aios-ui/tests/browser/m6-verify-review-closeout.spec.ts"),
      "m6-route-closeout",
      timestamps.closeout,
    );

    db.prepare("UPDATE sessions SET run_id = ? WHERE id = ?").run(ids.verifyRun, ids.verifySession);
    db.prepare("UPDATE sessions SET run_id = ? WHERE id = ?").run(ids.reviewRun, ids.reviewSession);
    db.prepare("UPDATE sessions SET run_id = ? WHERE id = ?").run(ids.closeoutRun, ids.closeoutSession);

    const insertEvent = db.prepare(
      `INSERT INTO orchestration_run_events
        (id, run_id, project_id, session_id, event_type, from_status, to_status, summary,
         reason_json, metadata_json, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', ?, ?)`,
    );
    insertEvent.run("m6-event-verify", ids.verifyRun, ids.project, ids.verifySession, "verify", "ready", "in_progress", "Verify lifecycle evidence recorded.", JSON.stringify({ evidenceIds: ["m6-evidence-browser-contract"] }), timestamps.verify);
    insertEvent.run("m6-event-review", ids.reviewRun, ids.project, ids.reviewSession, "review", "in_progress", "canceled", "Review lifecycle evidence awaits human authority.", JSON.stringify({ evidenceIds: ["m6-evidence-browser-contract"] }), timestamps.review);
    insertEvent.run("m6-event-closeout", ids.closeoutRun, ids.project, ids.closeoutSession, "closeout", "canceled", "completed", "Closeout lifecycle evidence recorded for the closed session.", JSON.stringify({ evidenceIds: ["m6-evidence-browser-contract", "m6-evidence-closeout"] }), timestamps.closeout);

    db.prepare(
      `INSERT INTO artifacts (id, session_id, artifact_type, path, metadata_json, created_at)
       VALUES (?, ?, 'closeout', ?, ?, ?)`,
    ).run(
      ids.closeoutArtifact,
      ids.closeoutSession,
      "aios-ui/tests/browser/m6-verify-review-closeout.spec.ts",
      JSON.stringify({ run_id: ids.closeoutRun, evidence_ids: ["m6-evidence-browser-contract", "m6-evidence-closeout"] }),
      timestamps.closeout,
    );

    db.prepare(
      `INSERT INTO improvement_writebacks (
         id, run_id, project_id, layer_type, layer_key, title, summary, evidence_json,
         proposed_change_json, impact_scope, status, requires_approval, approval_reason,
         token_regressive, created_at, updated_at
       ) VALUES (?, ?, ?, 'truth', 'm6-browser-contract', ?, ?, ?, ?,
         'project', 'pending_approval', 1, 'The review boundary requires an explicit owner decision.', 0, ?, ?)`,
    ).run(
      "m6-review-writeback",
      ids.reviewRun,
      ids.project,
      "Review M6 browser contract",
      "Review the seeded browser-contract evidence.",
      JSON.stringify(["m6-evidence-browser-contract"]),
      JSON.stringify({ run_id: ids.reviewRun, evidence_ids: ["m6-evidence-browser-contract"] }),
      timestamps.review,
      timestamps.review,
    );
  });

  seed();
  db.close();
};

const isSeeded = (): boolean => {
  if (!existsSync(M6_DATABASE_PATH)) {
    return false;
  }

  try {
    const db = new Database(M6_DATABASE_PATH, { readonly: true });
    const row = db
      .prepare("SELECT id FROM orchestration_runs WHERE id = ? AND status = 'completed' LIMIT 1")
      .get(M6_FIXTURE_IDS.closeoutRun) as { id: string } | undefined;
    db.close();
    return row?.id === M6_FIXTURE_IDS.closeoutRun;
  } catch {
    return false;
  }
};

export default async function globalSetup(_config: FullConfig): Promise<void> {
  process.env.AIOS_DB = M6_DATABASE_PATH;
  process.env.AIOS_ROOT = M6_REPO_ROOT;
  if (!isSeeded()) {
    seedDatabase();
  }
}

if (process.argv.includes("--m6-seed")) {
  process.env.AIOS_DB = M6_DATABASE_PATH;
  process.env.AIOS_ROOT = M6_REPO_ROOT;
  seedDatabase();
}
