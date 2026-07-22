import assert from "node:assert/strict";
import {
  mkdirSync,
  mkdtempSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";

const scanner = path.resolve(import.meta.dirname, "..", "bin", "trim-state-files.mjs");

test("skips generated audit trees and broken symlinks", () => {
  const root = mkdtempSync(path.join(os.tmpdir(), "trim-state-files-"));
  const oversizedState = `## Accumulated Context\n\n${"x".repeat(12_000)}\n`;

  try {
    const canonicalStateDir = path.join(root, "canonical", ".planning");
    mkdirSync(canonicalStateDir, { recursive: true });
    writeFileSync(path.join(canonicalStateDir, "STATE.md"), oversizedState);

    for (const generatedDir of [
      path.join(root, "data", "audit-worktrees", "run", ".planning"),
      path.join(root, "audit-environments", "run", ".planning"),
      path.join(root, ".audit-tmp", "run", ".tracker"),
    ]) {
      mkdirSync(generatedDir, { recursive: true });
      writeFileSync(
        path.join(generatedDir, generatedDir.endsWith(".tracker") ? "PROJECT_TRUTH.md" : "STATE.md"),
        oversizedState,
      );
    }

    const brokenLinkDir = path.join(root, "canonical", "broken");
    mkdirSync(brokenLinkDir, { recursive: true });
    symlinkSync(path.join(root, "missing-target"), path.join(brokenLinkDir, "STATE.md"));

    const result = spawnSync(process.execPath, [scanner, "--check", root], {
      encoding: "utf8",
    });
    const output = `${result.stdout}${result.stderr}`;

    assert.equal(result.status, 1);
    assert.match(output, /1 managed files/);
    assert.match(output, /canonical\/\.planning\/STATE\.md/);
    assert.doesNotMatch(output, /audit-worktrees|audit-environments|\.audit-tmp|ENOENT/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
