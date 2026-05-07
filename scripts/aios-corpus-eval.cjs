#!/usr/bin/env node
"use strict";

const childProcess = require("child_process");
const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");

const AIOS_ROOT = path.resolve(__dirname, "..");
const DEFAULT_CONFIG_PATH = path.join(AIOS_ROOT, "docs", "aios", "corpus", "config.json");
const DEFAULT_OUTPUT_ROOT = path.join(os.tmpdir(), "aios-corpus-evals");
const DEFAULT_TIMEOUT_MS = 30_000;
const LIVE_REFUSAL_EXIT = 8;

function nowIso() {
  return new Date().toISOString();
}

function usage() {
  return `Usage: node scripts/aios-corpus-eval.cjs [options]

Options:
  --dry-run                Print the plan without creating worktrees or executing commands.
  --sample                 Run commands and repos tagged for quick local iteration.
  --full                   Run every configured repo/mode/suite/command.
  --suite <name>           Run one suite.
  --repo <id>              Run one repo.
  --mode <name>            Run one evaluation mode.
  --keep-worktrees         Preserve temp workspaces for debugging.
  --timeout <ms>           Default per-command timeout.
  --json                   Print the JSON report path.
  --report-only <path>     Regenerate Markdown report from an existing JSON result.
  --config <path>          Use a non-default corpus config.
  --output-root <path>     Write evidence under this directory.
  --self-test              Run harness fixture checks.
  --help                   Show this help.
`;
}

function parseArgs(argv) {
  const args = {
    configPath: DEFAULT_CONFIG_PATH,
    outputRoot: DEFAULT_OUTPUT_ROOT,
    dryRun: false,
    sample: false,
    full: false,
    suite: null,
    repo: null,
    mode: null,
    keepWorktrees: false,
    timeoutMs: DEFAULT_TIMEOUT_MS,
    json: false,
    reportOnly: null,
    selfTest: false,
    help: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--dry-run") args.dryRun = true;
    else if (arg === "--sample") args.sample = true;
    else if (arg === "--full") args.full = true;
    else if (arg === "--keep-worktrees") args.keepWorktrees = true;
    else if (arg === "--json") args.json = true;
    else if (arg === "--self-test") args.selfTest = true;
    else if (arg === "--help" || arg === "-h") args.help = true;
    else if (arg === "--suite") args.suite = argv[++i];
    else if (arg === "--repo") args.repo = argv[++i];
    else if (arg === "--mode") args.mode = argv[++i];
    else if (arg === "--timeout") args.timeoutMs = Number(argv[++i]);
    else if (arg === "--config") args.configPath = path.resolve(argv[++i]);
    else if (arg === "--output-root") args.outputRoot = path.resolve(argv[++i]);
    else if (arg === "--report-only") args.reportOnly = path.resolve(argv[++i]);
    else throw new Error(`Unknown argument: ${arg}`);
  }

  if (!Number.isFinite(args.timeoutMs) || args.timeoutMs <= 0) {
    throw new Error("--timeout must be a positive number of milliseconds");
  }
  if (!args.sample && !args.full) args.sample = true;
  if (args.sample && args.full) throw new Error("Choose either --sample or --full, not both");
  return args;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function tokenMap(extra = {}) {
  return {
    aiosRoot: AIOS_ROOT,
    python: process.env.PYTHON || "python3",
    node: process.execPath,
    home: os.homedir(),
    ...extra,
  };
}

function expandTokens(value, tokens) {
  if (typeof value === "string") {
    return value.replace(/\{([a-zA-Z0-9_]+)\}/g, (match, key) => {
      if (Object.prototype.hasOwnProperty.call(tokens, key)) return String(tokens[key]);
      return match;
    });
  }
  if (Array.isArray(value)) return value.map((item) => expandTokens(item, tokens));
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, expandTokens(item, tokens)]),
    );
  }
  return value;
}

function loadConfig(configPath) {
  const raw = readJson(configPath);
  if (!Array.isArray(raw.repos)) throw new Error("config.repos must be an array");
  if (!Array.isArray(raw.commands)) throw new Error("config.commands must be an array");
  return raw;
}

function selectedCommands(config, args) {
  return config.commands.filter((command) => {
    if (args.suite && command.suite !== args.suite) return false;
    if (args.sample && command.sample === false) return false;
    return true;
  });
}

function selectedRepos(config, args) {
  return config.repos.filter((repo) => {
    if (args.repo && repo.id !== args.repo) return false;
    if (args.sample && repo.sample === false) return false;
    return true;
  });
}

function selectedModes(repo, args) {
  const modes = Array.isArray(repo.modes) ? repo.modes : [];
  return modes.filter((mode) => !args.mode || mode === args.mode);
}

function commandApplies(command, repo, mode) {
  if (Array.isArray(command.modes) && !command.modes.includes(mode)) return false;
  if (Array.isArray(command.repoTypes) && !command.repoTypes.includes(repo.type)) return false;
  if (Array.isArray(command.repoTags)) {
    const tags = new Set(repo.tags || []);
    if (!command.repoTags.some((tag) => tags.has(tag))) return false;
  }
  return true;
}

function buildPlan(config, args) {
  const repos = selectedRepos(config, args);
  const commands = selectedCommands(config, args);
  const plan = [];
  for (const repo of repos) {
    for (const mode of selectedModes(repo, args)) {
      const applicable = commands.filter((command) => commandApplies(command, repo, mode));
      for (const command of applicable) plan.push({ repo, mode, command });
    }
  }
  return plan;
}

function stableSlug(value) {
  return String(value).replace(/[^a-zA-Z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "");
}

function realpathIfExists(targetPath) {
  if (!targetPath || !fs.existsSync(targetPath)) return null;
  return fs.realpathSync(targetPath);
}

function isSameOrChild(candidate, parent) {
  const relative = path.relative(parent, candidate);
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function copyWorkspace(source, destination, mode) {
  const skipNames = new Set([
    ".git",
    ".venv",
    ".pnpm-store",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
  ]);
  fs.cpSync(source, destination, {
    recursive: true,
    filter: (src) => {
      const base = path.basename(src);
      if (skipNames.has(base)) return false;
      if (mode === "scratch-real" && [".tracker", ".superpowers"].includes(base)) return false;
      if (mode === "scratch-real" && src.includes(`${path.sep}data${path.sep}success-criteria${path.sep}`)) {
        return false;
      }
      return true;
    },
  });
}

function runProcess(argv, options = {}) {
  const started = process.hrtime.bigint();
  const spawn = childProcess.spawnSync(argv[0], argv.slice(1), {
    cwd: options.cwd,
    env: { ...process.env, ...(options.env || {}) },
    encoding: "utf8",
    timeout: options.timeoutMs,
    maxBuffer: 20 * 1024 * 1024,
  });
  const ended = process.hrtime.bigint();
  return {
    stdout: spawn.stdout || "",
    stderr: spawn.stderr || "",
    exitCode: typeof spawn.status === "number" ? spawn.status : null,
    signal: spawn.signal || null,
    error: spawn.error ? String(spawn.error.message || spawn.error) : null,
    timedOut: spawn.error && spawn.error.code === "ETIMEDOUT",
    durationMs: Number(ended - started) / 1_000_000,
  };
}

function runGit(args, cwd) {
  const result = runProcess(["git", ...args], { cwd, timeoutMs: 10_000 });
  return {
    ok: result.exitCode === 0,
    stdout: result.stdout.trim(),
    stderr: result.stderr.trim(),
    exitCode: result.exitCode,
  };
}

function initializeGitRepo(workspace, dirty) {
  runGit(["init"], workspace);
  runGit(["add", "."], workspace);
  runGit(
    [
      "-c",
      "user.email=corpus-eval@example.invalid",
      "-c",
      "user.name=AIOS Corpus Eval",
      "commit",
      "-m",
      "baseline corpus fixture",
    ],
    workspace,
  );
  if (dirty) {
    fs.writeFileSync(path.join(workspace, "dirty-note.txt"), "dirty fixture\n", "utf8");
  }
}

function createSyntheticFixture(repo, workspace) {
  fs.mkdirSync(workspace, { recursive: true });
  const fixture = repo.fixture || repo.id;
  if (fixture === "node-typescript") {
    fs.mkdirSync(path.join(workspace, "src"), { recursive: true });
    fs.writeFileSync(
      path.join(workspace, "package.json"),
      JSON.stringify(
        {
          name: "aios-corpus-node-typescript",
          version: "0.0.0",
          type: "module",
          scripts: { test: "node --test" },
          devDependencies: {},
        },
        null,
        2,
      ),
      "utf8",
    );
    fs.writeFileSync(path.join(workspace, "src", "index.ts"), "export const value = 42;\n", "utf8");
    fs.writeFileSync(path.join(workspace, "README.md"), "# Node TypeScript fixture\n", "utf8");
  } else if (fixture === "python-basic") {
    fs.mkdirSync(path.join(workspace, "src", "sample"), { recursive: true });
    fs.writeFileSync(path.join(workspace, "pyproject.toml"), "[project]\nname = \"fixture\"\nversion = \"0.0.0\"\n", "utf8");
    fs.writeFileSync(path.join(workspace, "src", "sample", "__init__.py"), "VALUE = 42\n", "utf8");
  } else if (fixture === "docs-only") {
    fs.mkdirSync(path.join(workspace, "docs"), { recursive: true });
    fs.writeFileSync(path.join(workspace, "README.md"), "# Docs-only fixture\n", "utf8");
    fs.writeFileSync(path.join(workspace, "docs", "guide.md"), "Use this for docs tests.\n", "utf8");
  } else if (fixture === "malformed-aios-state") {
    fs.mkdirSync(path.join(workspace, "config", "success-criteria"), { recursive: true });
    fs.writeFileSync(path.join(workspace, "config", "success-criteria", "registry.json"), "{bad json\n", "utf8");
    fs.writeFileSync(path.join(workspace, "README.md"), "# Malformed AIOS state fixture\n", "utf8");
  } else {
    fs.writeFileSync(path.join(workspace, "README.md"), `# ${fixture}\n`, "utf8");
  }
  initializeGitRepo(workspace, Boolean(repo.dirty));
}

function createSqliteDb(dbPath, workspace) {
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const script = `
import sqlite3
from pathlib import Path
db = Path(${JSON.stringify(dbPath)})
conn = sqlite3.connect(db)
conn.executescript("""
CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT, status TEXT, repo_path TEXT, obsidian_path TEXT);
CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, project_id TEXT, status TEXT, started_at TEXT, ended_at TEXT, cwd TEXT, objective TEXT, run_id TEXT, invocation_id TEXT, runtime_metadata_json TEXT DEFAULT '{}');
CREATE TABLE IF NOT EXISTS bug_log (id TEXT PRIMARY KEY, project_id TEXT, symptom TEXT, status TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS orchestration_runs (id TEXT PRIMARY KEY, project_id TEXT, session_id TEXT, objective TEXT, workflow_key TEXT, agent_key TEXT, status TEXT, rationale TEXT, assumptions_json TEXT DEFAULT '[]', context_trace_json TEXT DEFAULT '[]', backend_key TEXT, active_invocation_id TEXT, packet_id TEXT, status_reason_json TEXT DEFAULT '{}', created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS orchestration_invocations (id TEXT PRIMARY KEY, run_id TEXT, backend_key TEXT, backend_label TEXT, status TEXT, handshake_token TEXT, session_id TEXT, command_json TEXT DEFAULT '[]', metadata_json TEXT DEFAULT '{}', created_at TEXT, started_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS briefing_packets (id TEXT PRIMARY KEY, run_id TEXT, project_id TEXT, objective TEXT, workflow_key TEXT, agent_key TEXT, packet_markdown TEXT, sections_json TEXT DEFAULT '[]', policy_mode TEXT DEFAULT 'compact-ranked', token_budget INTEGER DEFAULT 900, selection_trace_json TEXT DEFAULT '[]', omitted_context_json TEXT DEFAULT '[]', created_at TEXT);
CREATE TABLE IF NOT EXISTS active_rules (title TEXT, body TEXT, domain TEXT, confidence REAL);
CREATE TABLE IF NOT EXISTS improvement_writebacks (id TEXT PRIMARY KEY, run_id TEXT, project_id TEXT, layer_type TEXT, layer_key TEXT, title TEXT, summary TEXT, evidence_json TEXT DEFAULT '[]', proposed_change_json TEXT DEFAULT '{}', status TEXT, requires_approval INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS knowledge_topics (id TEXT PRIMARY KEY, title TEXT, summary TEXT, canonical_href TEXT, confidence REAL, project_id TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS orchestration_run_events (id TEXT PRIMARY KEY, run_id TEXT, to_status TEXT, summary TEXT, reason_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS workflow_execution_reports (id TEXT PRIMARY KEY, run_id TEXT, invocation_id TEXT, workflow_key TEXT, status TEXT, artifact_path TEXT, created_at TEXT);
""")
conn.execute("INSERT OR IGNORE INTO projects (id, name, status, repo_path, obsidian_path) VALUES ('fixture', 'Corpus Fixture', 'active', ?, '')", (${JSON.stringify(workspace)},))
conn.execute("INSERT OR IGNORE INTO sessions (id, project_id, status, started_at, ended_at, cwd) VALUES ('session-fixture', 'fixture', 'closed', '2026-05-07T00:00:00Z', '2026-05-07T00:01:00Z', ?)", (${JSON.stringify(workspace)},))
conn.commit()
conn.close()
`;
  const result = runProcess([process.env.PYTHON || "python3", "-c", script], {
    cwd: workspace,
    timeoutMs: 10_000,
  });
  if (result.exitCode !== 0) throw new Error(`failed to create sqlite fixture: ${result.stderr}`);
}

function prepareWorkspace(repo, mode, runDir) {
  const workspace = path.join(runDir, "worktrees", `${stableSlug(repo.id)}-${stableSlug(mode)}`);
  const sourceRaw = repo.source ? expandTokens(repo.source, tokenMap()) : null;
  const source = sourceRaw ? path.resolve(sourceRaw) : null;
  if (repo.strategy === "synthetic-fixture") {
    createSyntheticFixture(repo, workspace);
  } else {
    if (!source || !fs.existsSync(source)) throw new Error(`repo ${repo.id} source does not exist: ${source}`);
    fs.mkdirSync(workspace, { recursive: true });
    copyWorkspace(source, workspace, mode);
    initializeGitRepo(workspace, Boolean(repo.dirty));
  }

  const stateRoot = path.join(workspace, ".aios-corpus-state");
  const stateData = path.join(stateRoot, "data");
  const stateLogs = path.join(stateRoot, "logs");
  fs.mkdirSync(stateData, { recursive: true });
  fs.mkdirSync(stateLogs, { recursive: true });
  const stateDb = path.join(stateData, "aios.db");
  const sourceDb = source ? path.join(source, "data", "aios.db") : null;
  if (mode === "migrated" && sourceDb && fs.existsSync(sourceDb)) {
    fs.copyFileSync(sourceDb, stateDb);
  } else {
    createSqliteDb(stateDb, workspace);
  }
  fs.writeFileSync(path.join(stateLogs, "hooks.log"), `${nowIso()} corpus fixture log\n`, "utf8");

  return { workspace, stateRoot, stateDb, stateLogs, source };
}

function listFiles(root) {
  const results = new Map();
  if (!fs.existsSync(root)) return results;
  const stack = [root];
  while (stack.length > 0) {
    const current = stack.pop();
    const entries = fs.readdirSync(current, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.name === ".git") continue;
      const full = path.join(current, entry.name);
      const rel = path.relative(root, full);
      if (entry.isDirectory()) {
        if (["node_modules", "__pycache__"].includes(entry.name)) continue;
        stack.push(full);
      } else if (entry.isFile()) {
        const stat = fs.statSync(full);
        results.set(rel, { size: stat.size, mtimeMs: Math.trunc(stat.mtimeMs) });
      }
    }
  }
  return results;
}

function changedFiles(before, after) {
  const changed = [];
  const keys = new Set([...before.keys(), ...after.keys()]);
  for (const key of [...keys].sort()) {
    const left = before.get(key);
    const right = after.get(key);
    if (!left) changed.push({ path: key, change: "added" });
    else if (!right) changed.push({ path: key, change: "deleted" });
    else if (left.size !== right.size || left.mtimeMs !== right.mtimeMs) {
      changed.push({ path: key, change: "modified" });
    }
  }
  return changed;
}

function gitSnapshot(workspace) {
  return {
    status: runGit(["status", "--short"], workspace),
    diffSummary: runGit(["diff", "--stat"], workspace),
  };
}

function parseJsonFromStdout(stdout) {
  const trimmed = stdout.trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed);
  } catch (_err) {
    const start = trimmed.indexOf("{");
    const end = trimmed.lastIndexOf("}");
    if (start >= 0 && end > start) {
      try {
        return JSON.parse(trimmed.slice(start, end + 1));
      } catch (_nested) {
        return null;
      }
    }
    return null;
  }
}

function classifyResult(command, execution, mutation) {
  if (!command) return { classification: "not-applicable", reason: "No matching command" };
  if (execution.timedOut) return { classification: "timeout", reason: "Command exceeded timeout" };
  if (execution.error && execution.exitCode === null) {
    return { classification: "harness-environment-issue", reason: execution.error };
  }
  if (mutation.unexpected.length > 0) {
    return {
      classification: "product-weakness",
      reason: `Unexpected mutations: ${mutation.unexpected.map((item) => item.path).slice(0, 5).join(", ")}`,
    };
  }
  const successExitCodes = Array.isArray(command.successExitCodes) ? command.successExitCodes : [0];
  if (successExitCodes.includes(execution.exitCode)) {
    return { classification: "pass", reason: `Exit code ${execution.exitCode}` };
  }
  if (command.expectedFailure) {
    return {
      classification: "expected-blocker",
      reason: `Expected non-success exit code ${execution.exitCode}`,
    };
  }
  if (execution.stderr.includes("No such file") || execution.stderr.includes("not found")) {
    return {
      classification: "harness-environment-issue",
      reason: `Command dependency failed with exit code ${execution.exitCode}`,
    };
  }
  return {
    classification: "product-weakness",
    reason: `Unexpected exit code ${execution.exitCode}`,
  };
}

function expectedMutationSet(command) {
  return new Set(command.expectedMutations || []);
}

function unexpectedMutations(changes, command) {
  if (command.allowAnyMutation) return [];
  const expected = expectedMutationSet(command);
  return changes.filter((item) => {
    if (expected.has(item.path)) return false;
    for (const prefix of expected) {
      if (prefix.endsWith("/") && item.path.startsWith(prefix)) return false;
    }
    return !item.path.startsWith(".git/");
  });
}

function commandTokens(prepared, repo, mode, outputDir) {
  return tokenMap({
    workspace: prepared.workspace,
    stateRoot: prepared.stateRoot,
    stateDb: prepared.stateDb,
    stateLogs: prepared.stateLogs,
    repoId: repo.id,
    repoType: repo.type,
    mode,
    outputDir,
  });
}

function writeText(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
}

function runCommand(planItem, prepared, runDir, args, config) {
  const { repo, mode, command } = planItem;
  if (!command) {
    return {
      repoId: repo.id,
      repoType: repo.type,
      mode,
      suite: null,
      commandName: null,
      classification: "not-applicable",
      classificationReason: planItem.notApplicableReason,
    };
  }

  const commandId = `${stableSlug(repo.id)}-${stableSlug(mode)}-${stableSlug(command.name)}`;
  const evidenceDir = path.join(runDir, "evidence", commandId);
  const tokens = commandTokens(prepared, repo, mode, evidenceDir);
  const argv = expandTokens(command.argv, tokens);
  const cwd = path.resolve(expandTokens(command.cwd || "{workspace}", tokens));
  const env = expandTokens({ ...(config.environment || {}), ...(command.env || {}) }, tokens);
  const timeoutMs = command.timeoutMs || args.timeoutMs || config.defaultTimeoutMs || DEFAULT_TIMEOUT_MS;

  const sourceReal = realpathIfExists(prepared.source);
  const cwdReal = realpathIfExists(cwd);
  if (sourceReal && cwdReal && cwdReal === sourceReal) {
    return {
      repoId: repo.id,
      repoType: repo.type,
      mode,
      suite: command.suite,
      commandName: command.name,
      commandString: argv.join(" "),
      cwd,
      classification: "harness-environment-issue",
      classificationReason: "Refused to execute inside a live source repo",
    };
  }

  const beforeFiles = listFiles(prepared.workspace);
  const beforeStateFiles = listFiles(prepared.stateRoot);
  const gitBefore = gitSnapshot(prepared.workspace);
  const execution = runProcess(argv, { cwd, env, timeoutMs });
  const gitAfter = gitSnapshot(prepared.workspace);
  const afterFiles = listFiles(prepared.workspace);
  const afterStateFiles = listFiles(prepared.stateRoot);
  const projectChanges = changedFiles(beforeFiles, afterFiles);
  const stateChanges = changedFiles(beforeStateFiles, afterStateFiles).map((item) => ({
    ...item,
    path: `.aios-corpus-state/${item.path}`,
  }));
  const allChanges = [...projectChanges, ...stateChanges];
  const mutation = { all: allChanges, unexpected: unexpectedMutations(allChanges, command) };
  const classification = classifyResult(command, execution, mutation);
  const parsedJson = command.parseJson === false ? null : parseJsonFromStdout(execution.stdout);

  const result = {
    repoId: repo.id,
    repoType: repo.type,
    mode,
    suite: command.suite,
    commandName: command.name,
    commandString: argv.join(" "),
    argv,
    cwd,
    env,
    exitCode: execution.exitCode,
    signal: execution.signal,
    durationMs: Math.round(execution.durationMs),
    timedOut: Boolean(execution.timedOut),
    parsedJson,
    artifactsWritten: allChanges,
    unexpectedMutations: mutation.unexpected,
    gitBefore,
    gitAfter,
    classification: classification.classification,
    classificationReason: classification.reason,
    evidencePath: evidenceDir,
  };

  writeText(path.join(evidenceDir, "stdout.txt"), execution.stdout);
  writeText(path.join(evidenceDir, "stderr.txt"), execution.stderr);
  writeJson(path.join(evidenceDir, "result.json"), result);
  return result;
}

function dryRun(config, plan, args) {
  const rows = plan.map(({ repo, mode, command }) => ({
    repo: repo.id,
    repoType: repo.type,
    mode,
    suite: command ? command.suite : null,
    command: command ? command.name : null,
    argv: command ? expandTokens(command.argv, tokenMap({ workspace: "<temp-workspace>" })).join(" ") : null,
  }));
  const payload = {
    generatedAt: nowIso(),
    configPath: args.configPath,
    selection: {
      sample: args.sample,
      full: args.full,
      suite: args.suite,
      repo: args.repo,
      mode: args.mode,
    },
    plannedCount: rows.length,
    plans: rows,
  };
  console.log(JSON.stringify(payload, null, 2));
}

function summarizeCounts(results, key) {
  const counts = {};
  for (const result of results) {
    const value = result[key] || "none";
    counts[value] = (counts[value] || 0) + 1;
  }
  return Object.fromEntries(Object.entries(counts).sort());
}

function commandScores(results) {
  const grouped = new Map();
  for (const result of results) {
    const key = result.commandName || "not-applicable";
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(result);
  }
  return [...grouped.entries()]
    .map(([name, rows]) => ({
      name,
      total: rows.length,
      pass: rows.filter((row) => row.classification === "pass").length,
      productWeakness: rows.filter((row) => row.classification === "product-weakness").length,
      expectedBlocker: rows.filter((row) => row.classification === "expected-blocker").length,
      timeout: rows.filter((row) => row.classification === "timeout").length,
    }))
    .sort((a, b) => b.pass - a.pass || a.productWeakness - b.productWeakness || a.name.localeCompare(b.name));
}

function repoTypeScores(results) {
  const grouped = new Map();
  for (const result of results) {
    const key = result.repoType || "unknown";
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(result);
  }
  return [...grouped.entries()]
    .map(([repoType, rows]) => ({
      repoType,
      total: rows.length,
      pass: rows.filter((row) => row.classification === "pass").length,
      weakness: rows.filter((row) => row.classification === "product-weakness").length,
      score: rows.length ? rows.filter((row) => row.classification === "pass").length / rows.length : 0,
    }))
    .sort((a, b) => b.score - a.score || a.repoType.localeCompare(b.repoType));
}

function buildBacklog(results) {
  const weaknesses = results.filter((result) =>
    ["product-weakness", "timeout", "harness-environment-issue"].includes(result.classification),
  );
  return weaknesses.slice(0, 20).map((result, index) => ({
    priority: index + 1,
    area: result.suite || "unknown",
    title: `${result.commandName || "command"} on ${result.repoId}/${result.mode}`,
    reason: result.classificationReason,
    evidencePath: result.evidencePath,
  }));
}

function makeReport(result) {
  const results = result.results || [];
  const scores = commandScores(results);
  const repoScores = repoTypeScores(results);
  const strongest = scores.filter((item) => item.total > 0 && item.pass === item.total).slice(0, 10);
  const weakest = scores.filter((item) => item.productWeakness > 0 || item.timeout > 0).slice(0, 10);
  const expectedBlockers = results.filter((item) => item.classification === "expected-blocker");
  const unclearOutput = results.filter((item) => item.classification === "product-weakness" && !item.parsedJson);
  const mutationFailures = results.filter((item) => (item.unexpectedMutations || []).length > 0);
  const timeoutProne = results.filter((item) => item.classification === "timeout");
  const backlog = buildBacklog(results);

  const lines = [];
  lines.push(`# AIOS Corpus Evaluation Report`);
  lines.push("");
  lines.push(`Generated: ${result.generatedAt}`);
  lines.push(`Run ID: ${result.runId}`);
  lines.push("");
  lines.push("## Counts");
  lines.push("");
  lines.push(`- By classification: \`${JSON.stringify(summarizeCounts(results, "classification"))}\``);
  lines.push(`- By suite: \`${JSON.stringify(summarizeCounts(results, "suite"))}\``);
  lines.push(`- By repo type: \`${JSON.stringify(summarizeCounts(results, "repoType"))}\``);
  lines.push(`- By mode: \`${JSON.stringify(summarizeCounts(results, "mode"))}\``);
  lines.push("");
  lines.push("## Strongest Commands");
  lines.push("");
  for (const item of strongest) lines.push(`- ${item.name}: ${item.pass}/${item.total} pass`);
  if (strongest.length === 0) lines.push("- None yet.");
  lines.push("");
  lines.push("## Commands Needing Product Improvement");
  lines.push("");
  for (const item of weakest) {
    lines.push(`- ${item.name}: ${item.productWeakness} product weaknesses, ${item.timeout} timeouts`);
  }
  if (weakest.length === 0) lines.push("- None detected.");
  lines.push("");
  lines.push("## Expected Blockers / Ergonomics Watchlist");
  lines.push("");
  for (const item of expectedBlockers.slice(0, 20)) {
    lines.push(`- ${item.commandName} on ${item.repoId}/${item.mode}: ${item.classificationReason}`);
  }
  if (expectedBlockers.length === 0) lines.push("- None recorded.");
  lines.push("");
  lines.push("## Repo-Type Fit");
  lines.push("");
  for (const item of repoScores) {
    lines.push(`- ${item.repoType}: ${item.pass}/${item.total} pass, ${item.weakness} weaknesses`);
  }
  lines.push("");
  lines.push("## Mutation Safety Failures");
  lines.push("");
  for (const item of mutationFailures.slice(0, 20)) {
    lines.push(`- ${item.commandName} on ${item.repoId}/${item.mode}: ${item.unexpectedMutations.map((m) => m.path).join(", ")}`);
  }
  if (mutationFailures.length === 0) lines.push("- None detected.");
  lines.push("");
  lines.push("## Timeout-Prone Commands");
  lines.push("");
  for (const item of timeoutProne.slice(0, 20)) lines.push(`- ${item.commandName} on ${item.repoId}/${item.mode}`);
  if (timeoutProne.length === 0) lines.push("- None detected.");
  lines.push("");
  lines.push("## Unclear Output Watchlist");
  lines.push("");
  for (const item of unclearOutput.slice(0, 20)) {
    lines.push(`- ${item.commandName} on ${item.repoId}/${item.mode}: ${item.evidencePath}`);
  }
  if (unclearOutput.length === 0) lines.push("- None detected.");
  lines.push("");
  lines.push("## Prioritized Improvement Backlog");
  lines.push("");
  for (const item of backlog) {
    lines.push(`${item.priority}. [${item.area}] ${item.title}: ${item.reason}`);
    lines.push(`   Evidence: ${item.evidencePath}`);
  }
  if (backlog.length === 0) lines.push("- No improvement backlog generated.");
  lines.push("");
  lines.push("## Raw Evidence");
  lines.push("");
  for (const item of results) {
    lines.push(`- ${item.repoId}/${item.mode}/${item.commandName}: ${item.evidencePath || "n/a"}`);
  }
  lines.push("");
  return `${lines.join("\n")}\n`;
}

function writeReports(runDir, result) {
  const jsonPath = path.join(runDir, "result.json");
  const markdownPath = path.join(runDir, "report.md");
  result.report = {
    countsByClassification: summarizeCounts(result.results, "classification"),
    countsBySuite: summarizeCounts(result.results, "suite"),
    countsByRepoType: summarizeCounts(result.results, "repoType"),
    countsByMode: summarizeCounts(result.results, "mode"),
    commandScores: commandScores(result.results),
    repoTypeScores: repoTypeScores(result.results),
    backlog: buildBacklog(result.results),
    markdownPath,
    jsonPath,
  };
  writeJson(jsonPath, result);
  writeText(markdownPath, makeReport(result));
  return { jsonPath, markdownPath };
}

function cleanupWorktrees(result, keepWorktrees) {
  if (keepWorktrees) return;
  for (const workspace of result.worktrees || []) {
    try {
      fs.rmSync(workspace, { recursive: true, force: true });
    } catch (_err) {
      // Best effort cleanup; the preserved evidence still records the path.
    }
  }
}

function runEvaluation(config, plan, args) {
  const runId = `corpus-${nowIso().replace(/[:.]/g, "-")}-${crypto.randomBytes(3).toString("hex")}`;
  const runDir = path.join(args.outputRoot, runId);
  fs.mkdirSync(runDir, { recursive: true });
  const result = {
    runId,
    generatedAt: nowIso(),
    configPath: args.configPath,
    runDir,
    selection: {
      sample: args.sample,
      full: args.full,
      suite: args.suite,
      repo: args.repo,
      mode: args.mode,
      keepWorktrees: args.keepWorktrees,
    },
    worktrees: [],
    results: [],
  };
  const preparedByRepoMode = new Map();
  for (const item of plan) {
    const key = `${item.repo.id}::${item.mode}`;
    let prepared = preparedByRepoMode.get(key);
    if (!prepared) {
      prepared = prepareWorkspace(item.repo, item.mode, runDir);
      preparedByRepoMode.set(key, prepared);
      result.worktrees.push(prepared.workspace);
    }
    const commandResult = runCommand(item, prepared, runDir, args, config);
    result.results.push(commandResult);
  }
  const paths = writeReports(runDir, result);
  cleanupWorktrees(result, args.keepWorktrees);
  return { result, ...paths };
}

function regenerateReport(jsonPath) {
  const result = readJson(jsonPath);
  const markdownPath = path.join(path.dirname(jsonPath), "report.md");
  writeText(markdownPath, makeReport(result));
  return markdownPath;
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function runSelfTest() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "aios-corpus-self-test-"));
  const configPath = path.join(tmp, "config.json");
  const outputRoot = path.join(tmp, "out");
  const config = {
    repos: [
      {
        id: "fixture",
        type: "docs-only",
        strategy: "synthetic-fixture",
        fixture: "docs-only",
        modes: ["synthetic"],
        sample: true,
      },
    ],
    commands: [
      {
        name: "node-version",
        suite: "cli-routing",
        argv: ["{node}", "--version"],
        modes: ["synthetic"],
        sample: true,
      },
      {
        name: "expected-failure",
        suite: "negative",
        argv: ["{node}", "--definitely-not-a-node-flag"],
        modes: ["synthetic"],
        expectedFailure: true,
        sample: true,
      },
    ],
  };
  writeJson(configPath, config);
  const args = parseArgs(["--sample", "--config", configPath, "--output-root", outputRoot]);
  const loaded = loadConfig(configPath);
  const plan = buildPlan(loaded, args);
  assert(plan.length === 2, "expected two planned commands");
  const run = runEvaluation(loaded, plan, args);
  const classes = run.result.results.map((item) => item.classification).sort();
  assert(classes.includes("pass"), "expected one pass");
  assert(classes.includes("expected-blocker"), "expected one expected blocker");
  const markdownPath = regenerateReport(run.jsonPath);
  assert(fs.existsSync(markdownPath), "expected regenerated report");
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log("self-test passed");
}

function main(argv) {
  const args = parseArgs(argv);
  if (args.help) {
    console.log(usage());
    return 0;
  }
  if (args.selfTest) {
    runSelfTest();
    return 0;
  }
  if (args.reportOnly) {
    const markdownPath = regenerateReport(args.reportOnly);
    if (args.json) console.log(JSON.stringify({ markdownPath }, null, 2));
    else console.log(`Regenerated ${markdownPath}`);
    return 0;
  }
  const config = loadConfig(args.configPath);
  const plan = buildPlan(config, args);
  if (plan.length === 0) throw new Error("No corpus commands selected");
  if (args.dryRun) {
    dryRun(config, plan, args);
    return 0;
  }
  const run = runEvaluation(config, plan, args);
  if (args.json) console.log(run.jsonPath);
  else {
    console.log(`JSON report: ${run.jsonPath}`);
    console.log(`Markdown report: ${run.markdownPath}`);
    if (args.keepWorktrees) {
      for (const workspace of run.result.worktrees) console.log(`Kept worktree: ${workspace}`);
    }
  }
  const counts = run.result.report.countsByClassification;
  return counts["harness-environment-issue"] > 0 ? LIVE_REFUSAL_EXIT : 0;
}

if (require.main === module) {
  try {
    process.exitCode = main(process.argv.slice(2));
  } catch (err) {
    console.error(err && err.stack ? err.stack : String(err));
    process.exitCode = 1;
  }
}

module.exports = {
  buildPlan,
  classifyResult,
  commandApplies,
  loadConfig,
  parseArgs,
  parseJsonFromStdout,
  regenerateReport,
  runEvaluation,
  selectedCommands,
  selectedModes,
  selectedRepos,
  unexpectedMutations,
};
