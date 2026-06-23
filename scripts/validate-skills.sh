#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

node --input-type=module <<'NODE'
import fs from "node:fs";

const manifestPath = "config/skills/macos-manifest.json";
const routerPath = "config/tmcp/macos-skills-router.json";
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const router = JSON.parse(fs.readFileSync(routerPath, "utf8"));
const nodes = [...manifest.nodes, ...manifest.modules];
const ids = nodes.map((node) => node.id);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(manifest.always_loaded === false, "macOS manifest must not be always-loaded");
assert(router.always_loaded === false, "macOS router must not be always-loaded");
assert(new Set(ids).size === ids.length, "macOS manifest has duplicate node IDs");

for (const node of nodes) {
  assert(fs.existsSync(node.path), `missing node path: ${node.path}`);
  assert(node.source_provenance, `missing source provenance: ${node.id}`);
  assert(node.source_provenance.source_path, `missing source path: ${node.id}`);
  assert(node.source_provenance.transformation_type, `missing transformation type: ${node.id}`);
}

for (const task of manifest.nodes) {
  assert(task.title, `missing title: ${task.id}`);
  assert(task.purpose, `missing purpose: ${task.id}`);
  assert(Array.isArray(task.triggers), `missing triggers: ${task.id}`);
  assert(Array.isArray(task.anti_triggers), `missing anti-triggers: ${task.id}`);
  assert(Array.isArray(task.dependencies), `missing dependencies: ${task.id}`);
  assert(Array.isArray(task.required_tools), `missing required tools: ${task.id}`);
  assert(Array.isArray(task.permission_gates), `missing permission gates: ${task.id}`);
  assert(Array.isArray(task.validation_commands), `missing validation commands: ${task.id}`);
  assert(task.freshness_note, `missing freshness note: ${task.id}`);
  for (const testPath of task.behavioral_tests) {
    assert(fs.existsSync(testPath), `missing behavioral test: ${testPath}`);
  }
}

for (const route of router.routes) {
  assert(Array.isArray(route.sequence), `missing route sequence: ${route.id}`);
  for (const ref of route.sequence) {
    if (ref.startsWith("@task:") || ref.startsWith("@module:")) {
      assert(ids.includes(ref), `route references unknown node: ${route.id} -> ${ref}`);
    }
  }
}

const releaseRoute = router.routes.find((route) => route.id === "macos_release_pipeline");
assert(releaseRoute, "missing macOS release route");
for (const gate of [
  "git_commit",
  "git_push",
  "gh_release_create",
  "appcast_mutation",
  "signing",
  "notarization",
  "artifact_publishing",
  "version_build_change"
]) {
  assert(releaseRoute.permission_gates.includes(gate), `missing release gate: ${gate}`);
}

const requiredTests = [
  ["tests/skills/macos/test_project_detection.md", ["Workspace Plus Project", "No Xcode Project", "Missing Scheme"]],
  ["tests/skills/macos/test_build_verify.md", ["BUILD SUCCEEDED", "Signing Identity Failure", "Post-Fix Rebuild"]],
  ["tests/skills/macos/test_native_pattern_routing.md", ["Menu Bar App", "Floating Overlay", "navigator.clipboard"]],
  ["tests/skills/macos/test_settings_window.md", ["New Settings Window", "macOS 26 Unavailable Fallback"]],
  ["tests/skills/macos/test_sparkle_auto_update.md", ["Missing Dependency", "Private Key Leakage"]],
  ["tests/skills/macos/test_notch_overlay.md", ["Notch Mac", "Incorrect visibleFrame Usage"]],
  ["tests/skills/macos/test_release_pipeline.md", ["Dry-Run Release", "Git Push Without Permission", "GitHub Release Without Permission"]]
];

for (const [testPath, needles] of requiredTests) {
  const text = fs.readFileSync(testPath, "utf8");
  for (const needle of needles) {
    assert(text.includes(needle), `missing behavioral scenario ${needle} in ${testPath}`);
  }
}

const scannedFiles = [
  manifestPath,
  routerPath,
  ...nodes.map((node) => node.path),
  ...requiredTests.map(([testPath]) => testPath)
];
const privateKeyPatterns = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
  /AGE-SECRET-KEY-[A-Z0-9]+/,
  /SPARKLE_PRIVATE_KEY\s*=/,
  /EDDSA_PRIVATE_KEY\s*=/
];
for (const path of scannedFiles) {
  const text = fs.readFileSync(path, "utf8");
  for (const pattern of privateKeyPatterns) {
    assert(!pattern.test(text), `private key pattern found in ${path}`);
  }
}

const broadTriggerText = JSON.stringify(router).toLowerCase();
assert(!broadTriggerText.includes("always load for any macos app"), "broad macOS always-load trigger found");
assert(!broadTriggerText.includes("load all macos modules"), "load-all macOS module trigger found");

console.log("macOS skill validation passed");
NODE
