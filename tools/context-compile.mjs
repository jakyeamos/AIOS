#!/usr/bin/env node
import { mkdir, readFile, readdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const REQUIRED_FIELDS = ["id", "title", "tier", "scope", "priority", "status", "summary", "applies_when", "tags"];
const VALID_TIERS = new Set(["global", "domain", "project", "feature", "packet", "handoff", "task", "evidence"]);
const VALID_PRIORITIES = new Set(["immutable", "high", "normal", "low", "deprecated"]);
const VALID_STATUSES = new Set(["active", "draft", "candidate", "deprecated", "archived"]);
const TIER_SPECIFICITY = {
  global: 0.55,
  domain: 0.65,
  project: 0.8,
  feature: 0.9,
  packet: 0.95,
  handoff: 0.75,
  task: 1,
  evidence: 0.7,
};
const PRIORITY_AUTHORITY = {
  immutable: 1,
  high: 0.85,
  normal: 0.65,
  low: 0.35,
  deprecated: 0.05,
};
const ALWAYS_LOAD_IDS = new Set(["context.index", "context.router", "context.schema", "handoffs.latest"]);

const SIGNALS = [
  {
    key: "task_touches_auth",
    terms: ["auth", "authentication", "oidc", "oauth", "login", "permission", "secret", "api key", "deployment"],
  },
  {
    key: "task_touches_api_keys",
    terms: ["api key", "api keys", "secret", "secrets", "credential", "credentials", "oidc"],
  },
  {
    key: "task_touches_user_data",
    terms: ["user data", "privacy", "personal", "pii", "vault", "obsidian"],
  },
  {
    key: "task_touches_permissions",
    terms: ["permission", "approval", "gate", "access", "policy"],
  },
  {
    key: "task_changes_core_logic",
    terms: ["compiler", "architecture", "refactor", "workflow", "standards delta", "health score", "routing"],
  },
  {
    key: "task_touches_testing",
    terms: ["test", "tests", "validation", "eval", "evaluation", "regression"],
  },
  {
    key: "task_touches_observability",
    terms: ["health", "score", "delta", "trace", "receipt", "inspect", "audit", "dashboard", "run history"],
  },
  {
    key: "task_touches_design",
    terms: ["ui", "drilldown", "drilldowns", "command center", "dashboard", "surface", "page"],
  },
  {
    key: "task_touches_web_app",
    terms: ["next", "react", "ui", "web", "dashboard", "deployment", "oidc"],
  },
  {
    key: "task_touches_data",
    terms: ["sqlite", "database", "data", "schema", "corpus", "metrics"],
  },
  {
    key: "task_touches_agent_harness",
    terms: ["agent", "workflow", "prompt", "skill", "evaluation", "eval", "packet", "compiler"],
  },
  {
    key: "task_touches_product_design",
    terms: ["product", "ux", "design", "drilldown", "command center", "health score"],
  },
  {
    key: "task_touches_knowledge_system",
    terms: ["knowledge", "obsidian", "second brain", "vault", "moc", "search", "retrieval", "context"],
  },
  {
    key: "task_touches_aios_ui",
    terms: ["aios ui", "dashboard", "health score", "standards delta", "critical delta", "command center"],
  },
  {
    key: "task_touches_taski",
    terms: ["taski"],
  },
  {
    key: "task_touches_terrace",
    terms: ["terrace"],
  },
  {
    key: "task_touches_soundscape",
    terms: ["soundscape"],
  },
  {
    key: "task_touches_context_compiler",
    terms: ["context compiler", "context", "routing", "briefing", "receipt", "markdown"],
  },
  {
    key: "task_touches_standards_delta",
    terms: ["standards delta", "critical delta", "health score", "project health"],
  },
  {
    key: "task_touches_prompt_library",
    terms: ["prompt", "prompt library", "prompt evaluation", "template"],
  },
  {
    key: "task_touches_skill_registry",
    terms: ["skill", "skill registry", "superpowers"],
  },
  {
    key: "task_touches_obsidian",
    terms: ["obsidian", "second brain", "vault", "moc", "backlink", "note"],
  },
];

const MISSING_CONTEXT_RULES = [
  {
    terms: ["critical delta", "health-score", "health score", "calculation"],
    requiredIds: ["features.health-score-calculation"],
    suggestedFile: "features/health-score-calculation.md",
    reason: "Task references critical delta or health-score calculation details, but no authoritative context file defines that calculation.",
  },
];

export function parseContextFile(filePath, content) {
  if (!content.startsWith("---\n")) {
    return { filePath, frontmatter: {}, body: content };
  }
  const end = content.indexOf("\n---", 4);
  if (end === -1) {
    return { filePath, frontmatter: {}, body: content };
  }
  const frontmatterText = content.slice(4, end).trimEnd();
  const body = content.slice(end + 4).replace(/^\n/, "");
  return { filePath, frontmatter: parseFrontmatter(frontmatterText), body };
}

function parseFrontmatter(text) {
  const root = {};
  const stack = [{ indent: -1, value: root }];
  let pendingKey = null;

  for (const rawLine of text.split(/\r?\n/)) {
    if (!rawLine.trim() || rawLine.trimStart().startsWith("#")) {
      continue;
    }
    const indent = rawLine.match(/^ */)[0].length;
    const line = rawLine.trim();
    while (stack.length > 1 && indent <= stack.at(-1).indent) {
      stack.pop();
    }
    const current = stack.at(-1).value;

    if (line.startsWith("- ")) {
      if (!Array.isArray(current)) {
        throw new Error(`Invalid frontmatter list item without list parent: ${rawLine}`);
      }
      current.push(coerceScalar(line.slice(2).trim()));
      continue;
    }

    const separator = line.indexOf(":");
    if (separator === -1) {
      continue;
    }
    const key = line.slice(0, separator).trim();
    const value = line.slice(separator + 1).trim();
    if (value === "") {
      const nextContainer = shouldCreateArray(text, rawLine) ? [] : {};
      current[key] = nextContainer;
      stack.push({ indent, value: nextContainer });
      pendingKey = key;
    } else {
      current[key] = coerceScalar(value);
      pendingKey = null;
    }
  }

  return root;
}

function shouldCreateArray(text, rawLine) {
  const lines = text.split(/\r?\n/);
  const index = lines.indexOf(rawLine);
  const baseIndent = rawLine.match(/^ */)[0].length;
  for (const laterLine of lines.slice(index + 1)) {
    if (!laterLine.trim()) {
      continue;
    }
    const indent = laterLine.match(/^ */)[0].length;
    if (indent <= baseIndent) {
      return false;
    }
    return laterLine.trim().startsWith("- ");
  }
  return false;
}

function coerceScalar(value) {
  const trimmed = value.trim();
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  if (/^\d+$/.test(trimmed)) return Number(trimmed);
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

export async function validateContextTree({ contextRoot }) {
  const files = await loadContextFiles(contextRoot);
  const errors = [];
  const ids = new Set();
  const relPaths = new Set(files.map((file) => file.relativePath));

  for (const file of files) {
    const fm = file.frontmatter;
    for (const field of REQUIRED_FIELDS) {
      if (fm[field] === undefined || fm[field] === "" || (Array.isArray(fm[field]) && fm[field].length === 0)) {
        errors.push(`${file.relativePath}: missing required field ${field}`);
      }
    }
    if (ids.has(fm.id)) {
      errors.push(`${file.relativePath}: duplicate id ${fm.id}`);
    }
    if (fm.id) ids.add(fm.id);
    if (fm.tier && !VALID_TIERS.has(fm.tier)) {
      errors.push(`${file.relativePath}: invalid tier ${fm.tier}`);
    }
    if (fm.priority && !VALID_PRIORITIES.has(fm.priority)) {
      errors.push(`${file.relativePath}: invalid priority ${fm.priority}`);
    }
    if (fm.status && !VALID_STATUSES.has(fm.status)) {
      errors.push(`${file.relativePath}: invalid status ${fm.status}`);
    }
    for (const listField of ["scope", "applies_when", "tags"]) {
      if (fm[listField] !== undefined && !Array.isArray(fm[listField])) {
        errors.push(`${file.relativePath}: ${listField} must be a list`);
      }
    }
    for (const linkedPath of asArray(fm.load_if_matched)) {
      if (!relPaths.has(linkedPath)) {
        errors.push(`${file.relativePath}: load_if_matched target missing: ${linkedPath}`);
      }
    }
    const explicitDeepPacket = fm.token_budget && Number(fm.token_budget) > 1200;
    if (estimateTokens(file.body) > 1200 && !explicitDeepPacket) {
      errors.push(`${file.relativePath}: context file is too large without token_budget > 1200`);
    }
  }

  return { ok: errors.length === 0, errors, files };
}

export async function compileContext({ task, contextRoot, write = true, outputRoot = contextRoot } = {}) {
  if (!task || !task.trim()) {
    throw new Error("--task is required");
  }
  const files = await loadContextFiles(contextRoot);
  const classification = classifyTask(task);
  const scored = scoreFiles(files, classification, task);
  const byRelativePath = new Map(files.map((file) => [file.relativePath, file]));
  const selected = new Map();

  for (const file of scored) {
    if (file.load_decision === "load") {
      selected.set(file.relativePath, file);
    }
  }

  for (const file of Array.from(selected.values())) {
    for (const linkedPath of asArray(file.frontmatter.load_if_matched)) {
      const linked = byRelativePath.get(linkedPath);
      if (linked) {
        selected.set(linked.relativePath, {
          ...linked,
          ...scoreOneFile(linked, classification, task),
          load_decision: "load",
          reason: `Loaded because ${file.frontmatter.id} matched and requested this packet.`,
        });
      }
    }
  }

  const selectedFiles = Array.from(selected.values()).sort(compareSelection);
  const selectedIds = new Set(selectedFiles.map((file) => file.frontmatter.id));
  const skippedFiles = scored
    .filter((file) => !selected.has(file.relativePath))
    .slice(0, 20)
    .map((file) => ({
      id: file.frontmatter.id,
      path: file.relativePath,
      reason: file.final_score > 0 ? "Scored below load threshold for this task." : "No task signal matched this context.",
    }));
  const conflicts = resolveConflicts(selectedFiles);
  const missingContext = detectMissingContext(task, selectedIds);
  const staleContext = detectStaleContext(selectedFiles);
  const writebackCandidates = [
    ...missingContext.map((item) => ({
      type: "missing_context",
      severity: "warning",
      suggested_file: item.suggested_file,
      reason: item.reason,
    })),
    ...staleContext.map((item) => ({
      type: "stale_context",
      severity: "warning",
      suggested_file: item.path,
      reason: `${item.id} was last reviewed on ${item.last_reviewed}.`,
    })),
  ];

  const payload = {
    task_summary: summarizeTask(task),
    task_classification: classification,
    selected_context_files: selectedFiles.map(toSelectedContext),
    relevant_rules: selectedFiles.map((file) => ({
      id: file.frontmatter.id,
      title: file.frontmatter.title,
      tier: file.frontmatter.tier,
      priority: file.frontmatter.priority,
      summary: file.frontmatter.summary,
    })),
    project_state: selectedFiles
      .filter((file) => file.frontmatter.tier === "project" || file.frontmatter.id === "handoffs.latest")
      .map((file) => `${file.frontmatter.title}: ${file.frontmatter.summary}`),
    feature_context: selectedFiles
      .filter((file) => file.frontmatter.tier === "feature" || file.frontmatter.tier === "packet")
      .map((file) => `${file.frontmatter.title}: ${file.frontmatter.summary}`),
    known_risks: buildKnownRisks(conflicts, missingContext, staleContext),
    acceptance_criteria: collectAcceptanceCriteria(selectedFiles),
    conflicts,
    stale_context: staleContext,
    missing_context: missingContext,
    writeback_candidates: writebackCandidates,
  };

  const briefingMarkdown = renderBriefing(payload);
  const receiptMarkdown = renderReceipt({
    task,
    loaded: selectedFiles,
    skipped: skippedFiles,
    conflicts,
    missingContext,
    writebackCandidates,
  });
  payload.context_receipt = receiptMarkdown;
  payload.briefing_markdown = briefingMarkdown;

  if (write) {
    await mkdir(path.join(outputRoot, "compiled"), { recursive: true });
    await mkdir(path.join(outputRoot, "receipts"), { recursive: true });
    await writeFile(path.join(outputRoot, "compiled", "latest.md"), briefingMarkdown);
    await writeFile(path.join(outputRoot, "compiled", "latest.json"), `${JSON.stringify(payload, null, 2)}\n`);
    await writeFile(path.join(outputRoot, "receipts", "latest.md"), receiptMarkdown);
    await writeFile(
      path.join(outputRoot, "receipts", "latest.json"),
      `${JSON.stringify(
        {
          task_summary: payload.task_summary,
          task_classification: payload.task_classification,
          selected_context_files: payload.selected_context_files,
          conflicts: payload.conflicts,
          stale_context: payload.stale_context,
          missing_context: payload.missing_context,
          writeback_candidates: payload.writeback_candidates,
          context_receipt: receiptMarkdown,
        },
        null,
        2,
      )}\n`,
    );
  }

  return payload;
}

export function classifyTask(task) {
  const lower = normalize(task);
  const matchedSignals = new Set(["all_tasks"]);
  const matchedTerms = [];
  for (const signal of SIGNALS) {
    for (const term of signal.terms) {
      if (lower.includes(term)) {
        matchedSignals.add(signal.key);
        matchedTerms.push(term);
        break;
      }
    }
  }
  const domains = [];
  if (matchedSignals.has("task_touches_web_app")) domains.push("web-apps");
  if (matchedSignals.has("task_touches_data")) domains.push("data-projects");
  if (matchedSignals.has("task_touches_agent_harness")) domains.push("agent-harnesses");
  if (matchedSignals.has("task_touches_product_design")) domains.push("product-design");
  if (matchedSignals.has("task_touches_knowledge_system")) domains.push("knowledge-systems");
  return {
    task,
    signals: Array.from(matchedSignals).sort(),
    domains,
    matched_terms: Array.from(new Set(matchedTerms)).sort(),
  };
}

async function loadContextFiles(contextRoot) {
  const markdownPaths = await walkMarkdown(contextRoot);
  const loaded = [];
  for (const absolutePath of markdownPaths) {
    const content = await readFile(absolutePath, "utf8");
    const parsed = parseContextFile(absolutePath, content);
    const relativePath = path.relative(contextRoot, absolutePath).split(path.sep).join("/");
    loaded.push({
      ...parsed,
      absolutePath,
      relativePath,
      token_cost_estimate: estimateTokens(content),
    });
  }
  return loaded;
}

async function walkMarkdown(root) {
  let entries = [];
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch {
    return [];
  }
  const files = [];
  for (const entry of entries) {
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      if (["compiled", "receipts"].includes(entry.name)) {
        continue;
      }
      files.push(...(await walkMarkdown(fullPath)));
    } else if (entry.isFile() && entry.name.endsWith(".md")) {
      files.push(fullPath);
    }
  }
  return files.sort();
}

function scoreFiles(files, classification, task) {
  return files.map((file) => ({ ...file, ...scoreOneFile(file, classification, task) })).sort((a, b) => b.final_score - a.final_score);
}

function scoreOneFile(file, classification, task) {
  const fm = file.frontmatter;
  const applies = asArray(fm.applies_when);
  const tags = asArray(fm.tags);
  const lowerTask = normalize(task);
  const signalMatches = applies.filter((signal) => classification.signals.includes(signal) || signal === "all_tasks").length;
  const tagMatches = tags.filter((tag) => lowerTask.includes(normalize(tag))).length;
  const titleMatches = tokenize(`${fm.id ?? ""} ${fm.title ?? ""} ${fm.summary ?? ""}`).filter((token) => lowerTask.includes(token)).length;
  const relevanceScore = Math.min(1, signalMatches * 0.38 + tagMatches * 0.22 + titleMatches * 0.08);
  const specificityScore = TIER_SPECIFICITY[fm.tier] ?? 0.4;
  const authorityScore = PRIORITY_AUTHORITY[fm.priority] ?? 0.4;
  const recencyScore = scoreRecency(fm.last_reviewed);
  const tokenCostPenalty = Math.min(1, file.token_cost_estimate / 1400);
  const finalScore = Number(
    (relevanceScore * 0.4 + specificityScore * 0.25 + authorityScore * 0.2 + recencyScore * 0.1 - tokenCostPenalty * 0.05).toFixed(4),
  );
  const forced = ALWAYS_LOAD_IDS.has(fm.id);
  const indexWithoutSignal = fm.id?.endsWith(".index") && signalMatches === 0;
  const hasTaskMatch = !indexWithoutSignal && (signalMatches > 0 || tagMatches > 0);
  const loadDecision = forced || (hasTaskMatch && finalScore >= 0.38) ? "load" : "skip";
  return {
    relevance_score: Number(relevanceScore.toFixed(4)),
    specificity_score: specificityScore,
    recency_score: recencyScore,
    authority_score: authorityScore,
    token_cost_estimate: file.token_cost_estimate,
    token_cost_penalty: Number(tokenCostPenalty.toFixed(4)),
    final_score: finalScore,
    load_decision: loadDecision,
    reason: forced ? "Bootloader context is always loaded." : reasonForScore(signalMatches, tagMatches, titleMatches, loadDecision),
  };
}

function reasonForScore(signalMatches, tagMatches, titleMatches, decision) {
  if (decision === "skip") return "No sufficient task, tag, or title overlap.";
  const parts = [];
  if (signalMatches) parts.push(`${signalMatches} applies_when signal(s) matched`);
  if (tagMatches) parts.push(`${tagMatches} tag(s) matched`);
  if (titleMatches) parts.push(`${titleMatches} title/summary term(s) matched`);
  return parts.join("; ") || "Selected by authority and tier defaults.";
}

function scoreRecency(value) {
  if (!value) return 0.25;
  const reviewed = Date.parse(value);
  if (Number.isNaN(reviewed)) return 0.25;
  const ageDays = (Date.now() - reviewed) / 86_400_000;
  if (ageDays <= 30) return 1;
  if (ageDays <= 90) return 0.8;
  if (ageDays <= 180) return 0.55;
  if (ageDays <= 365) return 0.35;
  return 0.15;
}

function resolveConflicts(selectedFiles) {
  const immutableProtections = selectedFiles
    .filter((file) => file.frontmatter.tier === "global" && file.frontmatter.priority === "immutable")
    .flatMap((file) => asArray(file.frontmatter.conflicts?.protected_topics).map((topic) => ({ topic, file })));
  const conflicts = [];
  for (const file of selectedFiles) {
    for (const weakenedTopic of asArray(file.frontmatter.conflicts?.weakens)) {
      const protectedMatch = immutableProtections.find((entry) => entry.topic === weakenedTopic);
      if (protectedMatch && protectedMatch.file.frontmatter.id !== file.frontmatter.id) {
        conflicts.push({
          topic: weakenedTopic,
          winner: protectedMatch.file.frontmatter.id,
          loser: file.frontmatter.id,
          resolution: "Global immutable rule keeps authority; the more specific file may add constraints but cannot weaken it.",
        });
      }
    }
  }
  return conflicts;
}

function detectMissingContext(task, selectedIds) {
  const lower = normalize(task);
  return MISSING_CONTEXT_RULES.filter((rule) => rule.terms.every((term) => lower.includes(normalize(term))))
    .filter((rule) => rule.requiredIds.every((id) => !selectedIds.has(id)))
    .map((rule) => ({
      type: "missing_context",
      severity: "warning",
      suggested_file: rule.suggestedFile,
      reason: rule.reason,
    }));
}

function detectStaleContext(selectedFiles) {
  return selectedFiles
    .filter((file) => {
      const value = file.frontmatter.last_reviewed;
      if (!value) return false;
      const reviewed = Date.parse(value);
      if (Number.isNaN(reviewed)) return false;
      return (Date.now() - reviewed) / 86_400_000 > 180;
    })
    .map((file) => ({
      id: file.frontmatter.id,
      path: file.relativePath,
      last_reviewed: file.frontmatter.last_reviewed,
    }));
}

function buildKnownRisks(conflicts, missingContext, staleContext) {
  const risks = [];
  if (conflicts.length) risks.push("One or more context conflicts were resolved by immutable global precedence.");
  if (missingContext.length) risks.push("Some requested concepts do not yet have authoritative context files.");
  if (staleContext.length) risks.push("Some selected context is stale and should be reviewed.");
  if (!risks.length) risks.push("No context-selection risks detected by the compiler.");
  return risks;
}

function collectAcceptanceCriteria(selectedFiles) {
  const criteria = [];
  for (const file of selectedFiles) {
    const matches = file.body.match(/## Acceptance Criteria\n([\s\S]*?)(\n## |$)/);
    if (!matches) continue;
    for (const line of matches[1].split(/\r?\n/)) {
      const trimmed = line.trim();
      if (trimmed.startsWith("- ")) {
        criteria.push(`${file.frontmatter.id}: ${trimmed.slice(2)}`);
      }
    }
  }
  return criteria.length ? criteria : ["Use the selected context receipt as the minimum execution contract."];
}

function toSelectedContext(file) {
  return {
    id: file.frontmatter.id,
    path: file.relativePath,
    title: file.frontmatter.title,
    tier: file.frontmatter.tier,
    priority: file.frontmatter.priority,
    relevance_score: file.relevance_score,
    specificity_score: file.specificity_score,
    recency_score: file.recency_score,
    authority_score: file.authority_score,
    token_cost_estimate: file.token_cost_estimate,
    final_score: file.final_score,
    load_decision: file.load_decision,
    reason: file.reason,
  };
}

function renderBriefing(payload) {
  return [
    "# AIOS Context Briefing",
    "",
    `## Task Summary`,
    "",
    payload.task_summary,
    "",
    "## Task Classification",
    "",
    `- Signals: ${payload.task_classification.signals.join(", ")}`,
    `- Domains: ${payload.task_classification.domains.join(", ") || "none"}`,
    "",
    "## Selected Context Files",
    "",
    ...payload.selected_context_files.map((file) => `- \`${file.path}\` (${file.id}) — ${file.reason}`),
    "",
    "## Relevant Rules",
    "",
    ...payload.relevant_rules.map((rule) => `- ${rule.id}: ${rule.summary}`),
    "",
    "## Project State",
    "",
    ...asMarkdownList(payload.project_state),
    "",
    "## Feature Context",
    "",
    ...asMarkdownList(payload.feature_context),
    "",
    "## Known Risks",
    "",
    ...asMarkdownList(payload.known_risks),
    "",
    "## Acceptance Criteria",
    "",
    ...asMarkdownList(payload.acceptance_criteria),
    "",
    "## Missing Context",
    "",
    ...asMarkdownList(payload.missing_context.map((item) => `${item.suggested_file}: ${item.reason}`)),
    "",
    "## Writeback Candidates",
    "",
    ...asMarkdownList(payload.writeback_candidates.map((item) => `${item.suggested_file}: ${item.reason}`)),
    "",
  ].join("\n");
}

function renderReceipt({ task, loaded, skipped, conflicts, missingContext, writebackCandidates }) {
  return [
    "# Context Receipt",
    "",
    "## Task",
    "",
    task,
    "",
    "## Loaded Context",
    "",
    ...loaded.map((file) => `- \`${file.relativePath}\`\n  - Reason: ${file.reason}`),
    "",
    "## Skipped Context",
    "",
    ...asMarkdownList(skipped.map((file) => `\`${file.path}\` — ${file.reason}`)),
    "",
    "## Conflicts",
    "",
    ...(conflicts.length ? conflicts.map((item) => `- ${item.topic}: ${item.winner} overrides ${item.loser}. ${item.resolution}`) : ["None detected."]),
    "",
    "## Missing Context",
    "",
    ...asMarkdownList(missingContext.map((item) => `${item.suggested_file}: ${item.reason}`)),
    "",
    "## Writeback Candidates",
    "",
    ...asMarkdownList(writebackCandidates.map((item) => `${item.suggested_file}: ${item.reason}`)),
    "",
  ].join("\n");
}

function asMarkdownList(items) {
  return items.length ? items.map((item) => `- ${item}`) : ["- None."];
}

function summarizeTask(task) {
  return task.trim().replace(/\s+/g, " ");
}

function normalize(value) {
  return String(value ?? "").toLowerCase().replace(/[_/-]+/g, " ");
}

function tokenize(value) {
  return normalize(value)
    .split(/[^a-z0-9]+/)
    .filter((token) => token.length >= 4);
}

function asArray(value) {
  if (value === undefined || value === null) return [];
  return Array.isArray(value) ? value : [value];
}

function estimateTokens(value) {
  return Math.ceil(String(value ?? "").split(/\s+/).filter(Boolean).length * 1.25);
}

function compareSelection(a, b) {
  const tierOrder = ["global", "domain", "project", "feature", "packet", "handoff", "task", "evidence"];
  const tierDelta = tierOrder.indexOf(a.frontmatter.tier) - tierOrder.indexOf(b.frontmatter.tier);
  if (tierDelta !== 0) return tierDelta;
  return b.final_score - a.final_score;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const repoRoot = path.resolve(import.meta.dirname, "..");
  const contextRoot = path.resolve(args.contextRoot ?? path.join(repoRoot, "aios", "context"));
  if (args.validate) {
    const result = await validateContextTree({ contextRoot });
    if (args.json) {
      console.log(JSON.stringify(result, null, 2));
    } else if (result.ok) {
      console.log(`Context validation passed for ${contextRoot}`);
    } else {
      console.error(result.errors.join("\n"));
    }
    process.exit(result.ok ? 0 : 1);
  }
  const result = await compileContext({
    task: args.task,
    contextRoot,
    write: args.write !== false,
  });
  if (args.json) {
    console.log(JSON.stringify(result, null, 2));
  } else {
    console.log(result.briefing_markdown);
  }
}

function parseArgs(argv) {
  const args = { write: true };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--task") {
      args.task = argv[++index];
    } else if (arg === "--context-root") {
      args.contextRoot = argv[++index];
    } else if (arg === "--json") {
      args.json = true;
    } else if (arg === "--validate") {
      args.validate = true;
    } else if (arg === "--no-write") {
      args.write = false;
    }
  }
  return args;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
}
