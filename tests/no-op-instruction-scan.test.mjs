import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { scanText } from "../tools/no-op-instruction-scan.mjs";

const repoRoot = path.resolve(import.meta.dirname, "..");

test("reports generic instruction clauses with file and line evidence", () => {
  const findings = scanText({
    filePath: "skills/example/SKILL.md",
    text: [
      "# Example",
      "",
      "Be thorough.",
      "Run `pnpm test` before reporting completion.",
    ].join("\n"),
  });

  assert.deepEqual(findings, [
    {
      file: "skills/example/SKILL.md",
      line: 3,
      pattern_id: "generic_thoroughness",
      category: "generic quality exhortation",
      clause: "Be thorough.",
    },
  ]);
});

test("ignores fenced examples and justified allowlist entries", () => {
  const findings = scanText({
    filePath: "skills/example/SKILL.md",
    text: [
      "# Example",
      "",
      "```markdown",
      "Be thorough.",
      "```",
      "",
      "Use best practices.",
      "Make the implementation robust.",
    ].join("\n"),
    allowlist: [
      {
        path: "skills/example/SKILL.md",
        line: 7,
        pattern_id: "generic_quality",
        reason: "Fixture intentionally demonstrates candidate phrasing.",
      },
      {
        path: "skills/example/SKILL.md",
        line: 8,
        pattern_id: "generic_robustness",
        reason: "Fixture intentionally demonstrates candidate phrasing.",
      },
    ],
  });

  assert.deepEqual(findings, []);
});

test("portable TMCP exposes instruction hygiene routing", async () => {
  const manifest = JSON.parse(
    await readFile(
      path.join(repoRoot, "config/tmcp/portable-dev-process/manifest.json"),
      "utf8",
    ),
  );
  const routingCases = JSON.parse(
    await readFile(
      path.join(repoRoot, "config/tmcp/portable-dev-process/tests/routing-cases.json"),
      "utf8",
    ),
  );

  assert.equal(
    manifest.nodes.tasks.instruction_hygiene.path,
    "tasks/instruction_hygiene.md",
  );
  assert.deepEqual(manifest.nodes.tasks.instruction_hygiene.requires, [
    "modules/instruction_hygiene.md",
    "modules/diff_review.md",
    "modules/quality_gate.md",
  ]);
  assert.equal(
    manifest.nodes.modules.instruction_hygiene,
    "modules/instruction_hygiene.md",
  );
  assert(
    routingCases.cases.some(
      (routingCase) => routingCase.expected_task === "instruction_hygiene",
    ),
  );
});
