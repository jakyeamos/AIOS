import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import {
  compileContext,
  parseContextFile,
  validateContextTree,
} from "../tools/context-compile.mjs";

const repoRoot = path.resolve(import.meta.dirname, "..");
const contextRoot = path.join(repoRoot, "aios", "context");

test("validates context frontmatter and link integrity", async () => {
  const result = await validateContextTree({ contextRoot });

  assert.equal(result.ok, true, result.errors.join("\n"));
  assert.equal(result.errors.length, 0);
});

test("selects UI standards-delta context for health score drilldown work", async () => {
  const result = await compileContext({
    task: "Improve the AIOS UI health score system so standards deltas are clearer.",
    contextRoot,
    write: false,
  });

  const selectedIds = result.selected_context_files.map((file) => file.id);
  assert(selectedIds.includes("global.maintainability"));
  assert(selectedIds.includes("global.observability"));
  assert(selectedIds.includes("global.design"));
  assert(selectedIds.includes("projects.aios-ui"));
  assert(selectedIds.includes("features.standards-delta"));
  assert(selectedIds.includes("packets.ui.command-center"));
  assert.match(result.context_receipt, /## Loaded Context/);
  assert.match(result.context_receipt, /## Skipped Context/);
});

test("follows load_if_matched links for OIDC secret handling", async () => {
  const result = await compileContext({
    task: "Implement OIDC-based secret handling for deployments.",
    contextRoot,
    write: false,
  });

  const selectedIds = result.selected_context_files.map((file) => file.id);
  assert(selectedIds.includes("global.security"));
  assert(selectedIds.includes("packets.security.oidc-secrets"));
  assert(selectedIds.includes("domains.web-apps"));
  assert(!selectedIds.includes("packets.ui.command-center"));
  assert(!selectedIds.includes("projects.soundscape"));
});

test("selects harness context for backend-neutral fake replay and shadow evaluation", async () => {
  const result = await compileContext({
    task: "Build a backend-neutral agent harness with fake lifecycle replay shadow evaluation and approval gates.",
    contextRoot,
    write: false,
  });

  const selectedIds = result.selected_context_files.map((file) => file.id);
  assert(selectedIds.includes("domains.agent-harnesses"));
  assert(selectedIds.includes("features.context-compiler"));
  assert(selectedIds.includes("config.agent-rules"));
  assert(
    result.selected_context_files.some((file) => file.path === "config/agent-rules.md"),
  );
  assert(selectedIds.includes("packets.workflow.approval-gates"));
  assert(selectedIds.includes("packets.testing.no-mock-echo"));
  assert.match(result.context_receipt, /config\/agent-rules\.md/);
  assert(!selectedIds.includes("projects.soundscape"));
});

test("selects agent prompt-library and skill-registry context for reusable prompt evaluation", async () => {
  const result = await compileContext({
    task: "Create a reusable prompt evaluation workflow for AIOS.",
    contextRoot,
    write: false,
  });

  const selectedIds = result.selected_context_files.map((file) => file.id);
  assert(selectedIds.includes("global.maintainability"));
  assert(selectedIds.includes("domains.agent-harnesses"));
  assert(selectedIds.includes("features.prompt-library"));
  assert(selectedIds.includes("features.skill-registry"));
});

test("selects knowledge-system and Obsidian routing context for second-brain search", async () => {
  const result = await compileContext({
    task: "Improve Obsidian search so AIOS can answer questions from my second brain.",
    contextRoot,
    write: false,
  });

  const selectedIds = result.selected_context_files.map((file) => file.id);
  assert(selectedIds.includes("domains.knowledge-systems"));
  assert(selectedIds.includes("features.obsidian-search"));
  assert(selectedIds.includes("packets.knowledge.obsidian-routing"));
});

test("immutable global conflicts are reported and resolved above weaker project rules", async () => {
  const tempRoot = await mkdtemp(path.join(tmpdir(), "aios-context-test-"));
  try {
    await mkdir(path.join(tempRoot, "standards"), { recursive: true });
    await mkdir(path.join(tempRoot, "projects"), { recursive: true });
    await writeFile(
      path.join(tempRoot, "standards", "global.security.md"),
      `---
id: global.security
title: Security
tier: global
scope:
  - all_projects
priority: immutable
status: active
summary: Secrets must not be committed.
applies_when:
  - task_touches_api_keys
tags:
  - security
  - secrets
conflicts:
  protected_topics:
    - secrets
---
Secrets must not be committed.
`,
    );
    await writeFile(
      path.join(tempRoot, "projects", "weak-project.md"),
      `---
id: projects.weak
title: Weak Project
tier: project
scope:
  - weak
priority: normal
status: active
summary: Convenience-only project rule.
applies_when:
  - task_touches_api_keys
tags:
  - security
  - secrets
conflicts:
  weakens:
    - secrets
---
Static secrets are acceptable for speed.
`,
    );

    const result = await compileContext({
      task: "Rotate API keys and update deployment secrets.",
      contextRoot: tempRoot,
      write: false,
    });

    assert.equal(result.conflicts.length, 1);
    assert.equal(result.conflicts[0].winner, "global.security");
    assert.equal(result.conflicts[0].loser, "projects.weak");
  } finally {
    await rm(tempRoot, { recursive: true, force: true });
  }
});

test("reports missing context for undefined health score calculation details", async () => {
  const result = await compileContext({
    task: "Improve critical delta health-score calculation drilldowns.",
    contextRoot,
    write: false,
  });

  assert(
    result.missing_context.some((item) => item.suggested_file === "features/health-score-calculation.md"),
  );
  assert(
    result.writeback_candidates.some((item) => item.suggested_file === "features/health-score-calculation.md"),
  );
});

test("writes latest briefing and receipt when requested", async () => {
  const tempRoot = await mkdtemp(path.join(tmpdir(), "aios-context-output-"));
  try {
    await mkdir(path.join(tempRoot, "standards"), { recursive: true });
    await writeFile(
      path.join(tempRoot, "standards", "global.maintainability.md"),
      `---
id: global.maintainability
title: Maintainability
tier: global
scope:
  - all_projects
priority: immutable
status: active
summary: Keep implementation simple.
applies_when:
  - all_tasks
tags:
  - maintainability
---
Keep implementation simple.
`,
    );

    await compileContext({
      task: "Refactor a small module.",
      contextRoot: tempRoot,
      write: true,
    });

    const briefing = await readFile(path.join(tempRoot, "compiled", "latest.md"), "utf8");
    const receipt = await readFile(path.join(tempRoot, "receipts", "latest.md"), "utf8");
    assert.match(briefing, /# AIOS Context Briefing/);
    assert.match(receipt, /# Context Receipt/);
  } finally {
    await rm(tempRoot, { recursive: true, force: true });
  }
});

test("emits packet-compatible retrieval trace and contract metadata", async () => {
  const result = await compileContext({
    task: "Improve Obsidian search so AIOS can answer questions from my second brain.",
    contextRoot,
    write: false,
  });

  assert.equal(result.packet_contract.route_compatible, true);
  assert.equal(result.packet_contract.selection_policy, "deterministic-context-compiler");
  assert(result.packet_contract.loaded_count >= 1);
  assert(result.retrieval_trace.some((item) => item.source === "domains.knowledge-systems"));
  assert(result.retrieval_trace.every((item) => typeof item.reason === "string" && item.reason.length > 0));
});

test("parses arrays, nested conflict keys, and body from frontmatter", async () => {
  const parsed = parseContextFile(
    "example.md",
    `---
id: example
title: Example
tier: packet
scope:
  - all_projects
priority: normal
status: active
summary: Example packet.
applies_when:
  - task_mentions_example
tags:
  - example
conflicts:
  weakens:
    - secrets
---
Body text.
`,
  );

  assert.deepEqual(parsed.frontmatter.scope, ["all_projects"]);
  assert.deepEqual(parsed.frontmatter.conflicts.weakens, ["secrets"]);
  assert.equal(parsed.body.trim(), "Body text.");
});
