#!/usr/bin/env node
import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export const DEFAULT_INCLUDE_PATTERNS = [
  /^AGENTS\.md$/,
  /^config\/agent-rules\.md$/,
  /^config\/tmcp\//,
  /^config\/workflows\//,
  /^prompts\//,
  /^skills\/.*(?:SKILL\.md|references\/.*\.md|agents\/.*\.ya?ml)$/,
  /^\.cursor\/skills\/.*\/SKILL\.md$/,
];

export const DEFAULT_EXCLUDE_PATTERNS = [
  /^config\/tmcp\/audits\//,
  /^skills-library\//,
  /^tmcp-benchmark\/runs\//,
  /^\.worktrees\//,
  /^logs\//,
  /^staging\//,
  /(?:^|\/)node_modules\//,
  /(?:^|\/)\.next\//,
  /(?:^|\/)__pycache__\//,
];

export const CANDIDATE_PATTERNS = [
  {
    id: "generic_thoroughness",
    category: "generic quality exhortation",
    regex: /\b(?:be thorough|be careful|think carefully|use good judgment)\b/i,
  },
  {
    id: "generic_quality",
    category: "generic quality exhortation",
    regex: /\b(?:high[- ]quality|produce high quality|quality work|best practices)\b/i,
  },
  {
    id: "generic_readability",
    category: "adjective-only requirement",
    regex: /\b(?:easy to read|make it clear|make it readable|readable implementation)\b/i,
  },
  {
    id: "generic_robustness",
    category: "adjective-only requirement",
    regex: /\b(?:robust|comprehensive)\b/i,
  },
  {
    id: "generic_commit_detail",
    category: "vague output requirement",
    regex: /\b(?:detailed commit message|very detailed commit|comprehensive commit)\b/i,
  },
];

function lineHasInlineAllowlist(line) {
  return /no-op-scan:\s*allow/i.test(line);
}

function inExcludedPath(filePath, excludePatterns = DEFAULT_EXCLUDE_PATTERNS) {
  return excludePatterns.some((pattern) => pattern.test(filePath));
}

function inIncludedPath(filePath, includePatterns = DEFAULT_INCLUDE_PATTERNS) {
  return includePatterns.some((pattern) => pattern.test(filePath));
}

function isAllowlisted(filePath, lineNumber, patternId, allowlist) {
  return allowlist.some((entry) => {
    if (entry.path !== filePath) {
      return false;
    }
    if (entry.pattern_id && entry.pattern_id !== patternId) {
      return false;
    }
    if (entry.line && entry.line !== lineNumber) {
      return false;
    }
    return Boolean(entry.reason);
  });
}

export function scanText({ filePath, text, allowlist = [] }) {
  const findings = [];
  const lines = text.split(/\r?\n/);
  let fenced = false;

  lines.forEach((line, index) => {
    const lineNumber = index + 1;
    if (/^\s*```/.test(line)) {
      fenced = !fenced;
      return;
    }
    if (fenced || lineHasInlineAllowlist(line)) {
      return;
    }

    for (const pattern of CANDIDATE_PATTERNS) {
      if (!pattern.regex.test(line)) {
        continue;
      }
      if (isAllowlisted(filePath, lineNumber, pattern.id, allowlist)) {
        continue;
      }
      findings.push({
        file: filePath,
        line: lineNumber,
        pattern_id: pattern.id,
        category: pattern.category,
        clause: line.trim(),
      });
    }
  });

  return findings;
}

async function trackedFiles(cwd) {
  const { stdout } = await execFileAsync(
    "git",
    ["ls-files", "--cached", "--others", "--exclude-standard"],
    { cwd, maxBuffer: 10 * 1024 * 1024 },
  );
  return stdout.split(/\r?\n/).filter(Boolean);
}

async function loadAllowlist(cwd, allowlistPath) {
  if (!allowlistPath) {
    return [];
  }
  const absolutePath = path.resolve(cwd, allowlistPath);
  const raw = await readFile(absolutePath, "utf8");
  const parsed = JSON.parse(raw);
  return Array.isArray(parsed.allowlist) ? parsed.allowlist : [];
}

export async function scanRepository({
  cwd = process.cwd(),
  allowlistPath = "config/tmcp/no-op-scan-allowlist.json",
} = {}) {
  const allowlist = await loadAllowlist(cwd, allowlistPath).catch(() => []);
  const files = (await trackedFiles(cwd)).filter(
    (filePath) => inIncludedPath(filePath) && !inExcludedPath(filePath),
  );
  const findings = [];

  for (const filePath of files) {
    const text = await readFile(path.join(cwd, filePath), "utf8");
    findings.push(...scanText({ filePath, text, allowlist }));
  }

  return { files_scanned: files.length, findings };
}

function parseArgs(argv) {
  const options = { format: "text", failOnCandidates: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--json") {
      options.format = "json";
    } else if (arg === "--fail-on-candidates") {
      options.failOnCandidates = true;
    } else if (arg === "--allowlist") {
      options.allowlistPath = argv[index + 1];
      index += 1;
    }
  }
  return options;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const result = await scanRepository({ allowlistPath: options.allowlistPath });

  if (options.format === "json") {
    console.log(JSON.stringify(result, null, 2));
  } else {
    console.log(`Scanned ${result.files_scanned} agent-facing instruction files.`);
    if (result.findings.length === 0) {
      console.log("No unallowlisted generic instruction candidates found.");
    } else {
      for (const finding of result.findings) {
        console.log(
          `${finding.file}:${finding.line} [${finding.pattern_id}] ${finding.clause}`,
        );
      }
    }
  }

  if (options.failOnCandidates && result.findings.length > 0) {
    process.exitCode = 1;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await main();
}
