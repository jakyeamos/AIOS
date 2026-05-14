import test from "node:test";
import assert from "node:assert/strict";

import {
  buildAgentPacket,
  emptyCorpusIndex,
  parseSourceRef,
  scoreWikiMaintenance,
  validateCorpusRef,
  validateWikiPages,
} from "../tools/wiki-check.mjs";

test("scores untrusted pages at 0", () => {
  assert.equal(scoreWikiMaintenance({ status: "current", confidence: "unknown" }), 0);
});

test("scores source-linked but unvalidated pages at 2", () => {
  assert.equal(
    scoreWikiMaintenance({
      status: "current",
      confidence: "medium",
      sourceRefs: [{ type: "doc", path: "PROJECT.md" }],
    }),
    2,
  );
});

test("scores script-validated checked pages at 5", () => {
  assert.equal(
    scoreWikiMaintenance({
      status: "current",
      confidence: "high",
      lastValidatedAt: "2026-05-14",
      validatedBy: "script",
      sourceCoverage: "partial",
      sourceRefs: [{ type: "doc", path: "PROJECT.md", lastCheckedAt: "2026-05-14" }],
    }),
    5,
  );
});

test("parses compact source refs with line ranges", () => {
  assert.deepEqual(parseSourceRef("code:services/foo.py#L10-L12|Foo service|2026-05-14"), {
    type: "code",
    path: "services/foo.py",
    label: "Foo service",
    lineStart: 10,
    lineEnd: 12,
    lastCheckedAt: "2026-05-14",
  });
});

test("agent packet includes verification checklist and source refs", () => {
  const packet = buildAgentPacket({
    id: "system-test",
    title: "Test System",
    path: "config/wiki-maintenance/critical-pages.json",
    status: "current",
    confidence: "high",
    lastValidatedAt: "2026-05-14",
    validatedBy: "agent",
    sourceRefs: [{ type: "doc", path: "PROJECT.md", label: "Project truth" }],
  });

  assert.equal(packet.subsystem, "Test System");
  assert.equal(packet.status, "current");
  assert.equal(packet.sourceFilesToInspect.length, 1);
  assert.match(packet.verificationChecklist.join("\n"), /pnpm wiki:check/);
});

test("drift check catches missing current source refs and broken paths", () => {
  const findings = validateWikiPages(
    [
      { id: "no-source", title: "No Source", status: "current", lastValidatedAt: "2026-05-14", sourceRefs: [] },
      {
        id: "broken-source",
        title: "Broken Source",
        status: "current",
        lastValidatedAt: "2026-05-14",
        sourceRefs: [{ type: "doc", path: "missing.md" }],
      },
    ],
    process.cwd(),
    new Set(),
  );

  assert.equal(findings.filter((finding) => finding.severity === "error").length, 2);
});

test("validates personal corpus refs against indexed ids", () => {
  const corpus = emptyCorpusIndex();
  corpus.patterns.add("pattern-1");
  corpus.sessions.add("session-1");
  corpus.memoryUpdates.add("memory-1");
  corpus.briefingPackets.add("packet-1");
  corpus.knowledgeTopics.add("topic-slug");
  corpus.importedConversations.add("conversation-slug");
  corpus.tasks.add("task-1");

  assert.equal(validateCorpusRef({ type: "pattern", path: "pattern-1" }, process.cwd(), corpus), true);
  assert.equal(validateCorpusRef({ type: "session", path: "session-1" }, process.cwd(), corpus), true);
  assert.equal(validateCorpusRef({ type: "memory_update", path: "memory-1" }, process.cwd(), corpus), true);
  assert.equal(validateCorpusRef({ type: "packet", path: "packet-1" }, process.cwd(), corpus), true);
  assert.equal(validateCorpusRef({ type: "knowledge_topic", path: "topic-slug" }, process.cwd(), corpus), true);
  assert.equal(validateCorpusRef({ type: "imported_conversation", path: "conversation-slug" }, process.cwd(), corpus), true);
  assert.equal(validateCorpusRef({ type: "task", path: "task-1" }, process.cwd(), corpus), true);
  assert.equal(validateCorpusRef({ type: "pattern", path: "missing" }, process.cwd(), corpus), false);
});

test("drift check catches unresolved personal corpus refs", () => {
  const findings = validateWikiPages(
    [
      {
        id: "corpus-source",
        title: "Corpus Source",
        status: "current",
        lastValidatedAt: "2026-05-14",
        sourceRefs: [
          { type: "pattern", path: "pattern-1" },
          { type: "session", path: "missing-session" },
        ],
      },
    ],
    process.cwd(),
    new Set(),
    {
      ...emptyCorpusIndex(),
      patterns: new Set(["pattern-1"]),
    },
  );

  assert.equal(findings.filter((finding) => finding.severity === "error").length, 1);
  assert.match(findings[0].message, /session:missing-session/);
});
