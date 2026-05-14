#!/usr/bin/env node
import { existsSync } from "node:fs";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const PAGE_STATUSES = new Set(["current", "planned", "deprecated", "historical", "experimental", "unverified"]);
const WARNING_STATUSES = new Set(["deprecated", "historical", "experimental", "unverified"]);

export function scoreWikiMaintenance(page) {
  const sourceRefs = page.sourceRefs ?? [];
  const hasSources = sourceRefs.length > 0;
  const hasFreshness = Boolean(page.lastIndexedAt || page.lastValidatedAt);
  const hasValidation = Boolean(page.lastValidatedAt);
  const confidence = page.confidence ?? "unknown";
  const status = normalizeStatus(page.status);
  const coverage = page.sourceCoverage ?? (sourceRefs.length > 0 ? "partial" : "none");
  const checkedRefs = sourceRefs.filter((ref) => ref.lastCheckedAt).length;

  if (!hasSources && !hasFreshness) return 0;
  if (!hasSources) return 1;
  if (!hasValidation || confidence === "unknown") return 2;
  if (status !== "unverified" && coverage !== "none") {
    if (page.validatedBy === "script" && checkedRefs === sourceRefs.length) return 5;
    if (page.validatedBy && page.validatedBy !== "unknown" && (page.knownStaleAreas ?? []).length === 0) return 4;
    return 3;
  }
  return 2;
}

export function parseSourceRef(value) {
  const [head, label, checked] = String(value).split("|").map((part) => part.trim());
  const separator = head.indexOf(":");
  if (separator === -1) return null;
  const type = head.slice(0, separator);
  const rawPath = head.slice(separator + 1);
  if (!rawPath) return null;
  const lineMatch = rawPath.match(/^(.*)#L(\d+)(?:-L?(\d+))?$/);
  return {
    type,
    path: lineMatch?.[1] ?? rawPath,
    label: label || undefined,
    lineStart: lineMatch?.[2] ? Number(lineMatch[2]) : undefined,
    lineEnd: lineMatch?.[3] ? Number(lineMatch[3]) : undefined,
    lastCheckedAt: checked || undefined,
  };
}

export function buildAgentPacket(page) {
  const sourceRefs = page.sourceRefs ?? [];
  return {
    subsystem: page.title,
    status: normalizeStatus(page.status),
    confidence: page.confidence ?? "unknown",
    maintenanceScore: scoreWikiMaintenance(page),
    lastValidated: page.lastValidatedAt ?? "not validated",
    knownStaleAreas: page.knownStaleAreas ?? [],
    relevantWikiPages: [{ title: page.title, path: page.path, status: normalizeStatus(page.status) }],
    sourceFilesToInspect: sourceRefs,
    applicableStandards: [
      "Use wiki/context pages as maps, not source of truth.",
      "Read referenced source files before editing behavior.",
      "Run relevant tests, typecheck, lint, or validation scripts after changes.",
    ],
    knownRisks: [
      ...((page.knownStaleAreas ?? []).map((area) => `Known stale area: ${area}`)),
      ...(WARNING_STATUSES.has(normalizeStatus(page.status))
        ? [`Page is ${normalizeStatus(page.status)}; verify source before treating it as current.`]
        : []),
      ...(sourceRefs.length === 0 ? ["No source refs are attached."] : []),
    ],
    currentVsPlannedNotes: [`Page status is ${normalizeStatus(page.status)}.`],
    verificationChecklist: [
      "Use this packet to decide where to look; do not treat it as proof.",
      "Inspect source refs before acting.",
      "Run `pnpm context:validate` when context packets or routing files change.",
      "Run `pnpm wiki:check` after wiki metadata or source refs change.",
      "Update wiki metadata or project truth when architecture, commands, APIs, workflows, rules, risks, or failure modes changed.",
    ],
  };
}

export function validateWikiPages(pages, repoRoot, packageScripts = new Set()) {
  const findings = [];
  for (const page of pages) {
    const status = normalizeStatus(page.status);
    const refs = page.sourceRefs ?? [];
    if (!PAGE_STATUSES.has(status)) {
      findings.push(error(page, `invalid status: ${page.status}`));
    }
    if (status === "current" && refs.length === 0) {
      findings.push(error(page, "current page has no sourceRefs"));
    }
    if (!page.lastValidatedAt) {
      findings.push(warn(page, "missing lastValidatedAt"));
    }
    if (WARNING_STATUSES.has(status)) {
      findings.push(warn(page, `${status} page must be treated as non-current context`));
    }
    for (const ref of refs) {
      if (!ref.path) {
        findings.push(error(page, "sourceRef is missing path"));
        continue;
      }
      if (ref.type !== "external" && !ref.path.startsWith("http")) {
        const fullPath = path.isAbsolute(ref.path) ? ref.path : path.join(repoRoot, ref.path);
        if (!existsSync(fullPath)) {
          findings.push(error(page, `sourceRef path does not exist: ${ref.path}`));
        }
      }
    }
    for (const command of page.commands ?? []) {
      const script = command.replace(/^pnpm\s+/, "").replace(/^run\s+/, "").trim();
      if (script && !packageScripts.has(script)) {
        findings.push(warn(page, `referenced pnpm command is not in package scripts: ${command}`));
      }
    }
  }
  return findings;
}

async function main() {
  const repoRoot = path.resolve(import.meta.dirname, "..");
  const packageScripts = await loadPackageScripts(repoRoot);
  const pages = [
    ...(await loadCriticalPages(repoRoot)),
    ...(await loadContextPages(repoRoot)),
    ...(await loadVaultWikiPages(repoRoot)),
  ];
  const findings = validateWikiPages(pages, repoRoot, packageScripts);
  const errors = findings.filter((finding) => finding.severity === "error");
  const warnings = findings.filter((finding) => finding.severity === "warning");

  console.log(`Wiki maintenance check: ${pages.length} pages checked, ${errors.length} errors, ${warnings.length} warnings`);
  for (const finding of findings) {
    console.log(`${finding.severity.toUpperCase()} ${finding.pageId}: ${finding.message}`);
  }

  process.exit(errors.length > 0 ? 1 : 0);
}

async function loadCriticalPages(repoRoot) {
  const filePath = path.join(repoRoot, "config", "wiki-maintenance", "critical-pages.json");
  if (!existsSync(filePath)) return [];
  const parsed = JSON.parse(await readFile(filePath, "utf8"));
  return (parsed.pages ?? []).map((page) => ({
    ...page,
    path: "config/wiki-maintenance/critical-pages.json",
    confidence: page.confidence ?? "high",
    validatedBy: page.validatedBy ?? "agent",
    sourceCoverage: page.sourceCoverage ?? "partial",
  }));
}

async function loadContextPages(repoRoot) {
  const contextRoot = path.join(repoRoot, "aios", "context");
  const files = await walkMarkdown(contextRoot);
  const pages = [];
  for (const filePath of files) {
    const content = await readFile(filePath, "utf8");
    const frontmatter = parseFrontmatter(content);
    const sourceRefs = getList(content, "source_refs").map(parseSourceRef).filter(Boolean);
    pages.push({
      id: frontmatter.id ?? path.relative(repoRoot, filePath),
      title: frontmatter.title ?? path.basename(filePath),
      path: path.relative(repoRoot, filePath),
      status: frontmatter.wiki_status ?? "unverified",
      confidence: frontmatter.wiki_confidence ?? "unknown",
      lastIndexedAt: frontmatter.last_reviewed,
      lastValidatedAt: frontmatter.last_validated_at ?? frontmatter.last_reviewed,
      validatedBy: frontmatter.validated_by ?? "unknown",
      sourceRefs,
      sourceCoverage: frontmatter.source_coverage,
      knownStaleAreas: getList(content, "known_stale_areas"),
      commands: extractPnpmCommands(content),
    });
  }
  return pages;
}

async function loadVaultWikiPages(repoRoot) {
  const vaultRoot = process.env.AIOS_VAULT_ROOT
    ? expandHome(process.env.AIOS_VAULT_ROOT)
    : path.join(process.env.HOME ?? "", "Vaults", "Command-Center");
  const wikiRoot = path.join(vaultRoot, "06 Knowledge", "Wiki");
  if (!existsSync(wikiRoot)) return [];
  const files = await walkMarkdown(wikiRoot);
  const pages = [];
  for (const filePath of files) {
    const content = await readFile(filePath, "utf8");
    const frontmatter = parseFrontmatter(content);
    const sourceRefs = getList(content, "source_refs").map(parseSourceRef).filter(Boolean);
    pages.push({
      id: `vault:${path.basename(filePath, ".md")}`,
      title: frontmatter.title ?? path.basename(filePath, ".md"),
      path: path.relative(repoRoot, filePath),
      status: frontmatter.wiki_status ?? "unverified",
      confidence: frontmatter.wiki_confidence ?? frontmatter.confidence ?? "unknown",
      lastIndexedAt: frontmatter.updated ?? frontmatter.created,
      lastValidatedAt: frontmatter.last_validated_at,
      validatedBy: frontmatter.validated_by ?? "unknown",
      sourceRefs,
      sourceCoverage: frontmatter.source_coverage,
      knownStaleAreas: getList(content, "known_stale_areas"),
      commands: extractPnpmCommands(content),
    });
  }
  return pages;
}

async function loadPackageScripts(repoRoot) {
  const scripts = new Set();
  for (const packagePath of [path.join(repoRoot, "package.json"), path.join(repoRoot, "aios-ui", "package.json")]) {
    if (!existsSync(packagePath)) continue;
    const parsed = JSON.parse(await readFile(packagePath, "utf8"));
    for (const script of Object.keys(parsed.scripts ?? {})) {
      scripts.add(script);
    }
  }
  return scripts;
}

async function walkMarkdown(root) {
  if (!existsSync(root)) return [];
  const entries = await readdir(root, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      if (["compiled", "receipts"].includes(entry.name)) continue;
      files.push(...(await walkMarkdown(fullPath)));
    } else if (entry.isFile() && entry.name.endsWith(".md")) {
      files.push(fullPath);
    }
  }
  return files.sort();
}

function parseFrontmatter(content) {
  if (!content.startsWith("---\n")) return {};
  const end = content.indexOf("\n---", 4);
  if (end === -1) return {};
  const output = {};
  for (const line of content.slice(4, end).split(/\r?\n/)) {
    const separator = line.indexOf(":");
    if (separator === -1 || line.trim().startsWith("- ")) continue;
    output[line.slice(0, separator).trim()] = line.slice(separator + 1).trim();
  }
  return output;
}

function getList(content, key) {
  if (!content.startsWith("---\n")) return [];
  const end = content.indexOf("\n---", 4);
  if (end === -1) return [];
  const frontmatter = content.slice(0, end + 4);
  const match = frontmatter.match(new RegExp(`^${key}:\\s*\\n((?:\\s+-\\s+.+\\n?)*)`, "m"));
  if (!match?.[1]) return [];
  return match[1]
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("- "))
    .map((line) => line.slice(2).trim());
}

function extractPnpmCommands(content) {
  const commands = new Set();
  for (const match of content.matchAll(/`(pnpm(?:\s+run)?\s+[a-z0-9:_-]+)`/gi)) {
    commands.add(match[1]);
  }
  return Array.from(commands);
}

function normalizeStatus(value) {
  if (PAGE_STATUSES.has(value)) return value;
  if (["active", "accepted", "approved"].includes(value)) return "current";
  if (["draft", "candidate", "proposed"].includes(value)) return "planned";
  if (value === "archived") return "historical";
  return "unverified";
}

function expandHome(value) {
  return value.replace(/^~(?=$|\/)/, process.env.HOME ?? "");
}

function error(page, message) {
  return { severity: "error", pageId: page.id, message };
}

function warn(page, message) {
  return { severity: "warning", pageId: page.id, message };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
