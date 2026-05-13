import { readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";

type SelectedContextFile = {
  id: string;
  path: string;
  title: string;
  tier: string;
  priority: string;
  relevance_score: number;
  specificity_score: number;
  recency_score: number;
  authority_score: number;
  token_cost_estimate: number;
  final_score: number;
  load_decision: string;
  reason: string;
};

type ContextIssue = {
  type?: string;
  severity?: string;
  suggested_file?: string;
  reason: string;
};

type ContextConflict = {
  topic: string;
  winner: string;
  loser: string;
  resolution: string;
};

type CompiledContextPayload = {
  task_summary: string;
  task_classification: {
    signals: string[];
    domains: string[];
    matched_terms?: string[];
  };
  selected_context_files: SelectedContextFile[];
  conflicts: ContextConflict[];
  stale_context: Array<{ id: string; path: string; last_reviewed: string }>;
  missing_context: ContextIssue[];
  writeback_candidates: ContextIssue[];
  context_receipt: string;
};

export type ContextCompilerFileSummary = {
  id: string;
  title: string;
  tier: string;
  priority: string;
  status: string;
  path: string;
};

export type ContextCompilerOverview = {
  exists: boolean;
  contextRoot: string;
  compiledPath: string;
  receiptPath: string;
  generatedAt: string | null;
  taskSummary: string;
  signals: string[];
  domains: string[];
  loadedFiles: SelectedContextFile[];
  skippedContext: string[];
  conflicts: ContextConflict[];
  staleContext: Array<{ id: string; path: string; lastReviewed: string }>;
  missingContext: ContextIssue[];
  writebackCandidates: ContextIssue[];
  receiptMarkdown: string;
  inventory: {
    totalFiles: number;
    byTier: Array<{ tier: string; count: number }>;
    files: ContextCompilerFileSummary[];
  };
};

const resolveRepoRoot = (): string => {
  if (path.basename(process.cwd()) === "aios-ui") {
    return path.resolve(process.cwd(), "..");
  }

  return process.cwd();
};

const readJson = async (filePath: string): Promise<unknown | null> => {
  try {
    return JSON.parse(await readFile(filePath, "utf8")) as unknown;
  } catch {
    return null;
  }
};

const asRecord = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};

const asString = (value: unknown, fallback = ""): string => (typeof value === "string" ? value : fallback);

const asNumber = (value: unknown): number => (typeof value === "number" ? value : 0);

const asStringArray = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];

const parseSelectedFile = (value: unknown): SelectedContextFile => {
  const record = asRecord(value);

  return {
    id: asString(record.id),
    path: asString(record.path),
    title: asString(record.title),
    tier: asString(record.tier),
    priority: asString(record.priority),
    relevance_score: asNumber(record.relevance_score),
    specificity_score: asNumber(record.specificity_score),
    recency_score: asNumber(record.recency_score),
    authority_score: asNumber(record.authority_score),
    token_cost_estimate: asNumber(record.token_cost_estimate),
    final_score: asNumber(record.final_score),
    load_decision: asString(record.load_decision),
    reason: asString(record.reason),
  };
};

const parseIssue = (value: unknown): ContextIssue => {
  const record = asRecord(value);

  return {
    type: typeof record.type === "string" ? record.type : undefined,
    severity: typeof record.severity === "string" ? record.severity : undefined,
    suggested_file: typeof record.suggested_file === "string" ? record.suggested_file : undefined,
    reason: asString(record.reason, "No reason recorded."),
  };
};

const parseConflict = (value: unknown): ContextConflict => {
  const record = asRecord(value);

  return {
    topic: asString(record.topic),
    winner: asString(record.winner),
    loser: asString(record.loser),
    resolution: asString(record.resolution),
  };
};

const parseCompiledPayload = (value: unknown): CompiledContextPayload | null => {
  const record = asRecord(value);
  if (!record.task_summary || !record.task_classification) {
    return null;
  }

  const classification = asRecord(record.task_classification);

  return {
    task_summary: asString(record.task_summary),
    task_classification: {
      signals: asStringArray(classification.signals),
      domains: asStringArray(classification.domains),
      matched_terms: asStringArray(classification.matched_terms),
    },
    selected_context_files: Array.isArray(record.selected_context_files)
      ? record.selected_context_files.map(parseSelectedFile)
      : [],
    conflicts: Array.isArray(record.conflicts) ? record.conflicts.map(parseConflict) : [],
    stale_context: Array.isArray(record.stale_context)
      ? record.stale_context.map((item) => {
          const stale = asRecord(item);
          return {
            id: asString(stale.id),
            path: asString(stale.path),
            last_reviewed: asString(stale.last_reviewed),
          };
        })
      : [],
    missing_context: Array.isArray(record.missing_context) ? record.missing_context.map(parseIssue) : [],
    writeback_candidates: Array.isArray(record.writeback_candidates)
      ? record.writeback_candidates.map(parseIssue)
      : [],
    context_receipt: asString(record.context_receipt),
  };
};

const parseFrontmatterValue = (content: string, key: string): string => {
  const match = content.match(new RegExp(`^${key}:\\s*(.+)$`, "m"));
  return match?.[1]?.trim() ?? "";
};

const walkMarkdown = async (root: string): Promise<string[]> => {
  let entries;
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch {
    return [];
  }

  const files = await Promise.all(
    entries.map(async (entry) => {
      const entryPath = path.join(root, entry.name);
      if (entry.isDirectory()) {
        if (entry.name === "compiled" || entry.name === "receipts") {
          return [];
        }
        return walkMarkdown(entryPath);
      }

      return entry.isFile() && entry.name.endsWith(".md") ? [entryPath] : [];
    }),
  );

  return files.flat().sort();
};

const loadInventory = async (contextRoot: string): Promise<ContextCompilerOverview["inventory"]> => {
  const markdownFiles = await walkMarkdown(contextRoot);
  const files = await Promise.all(
    markdownFiles.map(async (filePath) => {
      const content = await readFile(filePath, "utf8");

      return {
        id: parseFrontmatterValue(content, "id"),
        title: parseFrontmatterValue(content, "title"),
        tier: parseFrontmatterValue(content, "tier"),
        priority: parseFrontmatterValue(content, "priority"),
        status: parseFrontmatterValue(content, "status"),
        path: path.relative(contextRoot, filePath).split(path.sep).join("/"),
      };
    }),
  );
  const tierCounts = new Map<string, number>();
  for (const file of files) {
    tierCounts.set(file.tier, (tierCounts.get(file.tier) ?? 0) + 1);
  }

  return {
    totalFiles: files.length,
    byTier: Array.from(tierCounts.entries())
      .map(([tier, count]) => ({ tier, count }))
      .sort((left, right) => left.tier.localeCompare(right.tier)),
    files,
  };
};

const extractSkippedContext = (receiptMarkdown: string): string[] => {
  const section = receiptMarkdown.match(/## Skipped Context\n\n([\s\S]*?)(\n## |$)/);
  if (!section) {
    return [];
  }

  return section[1]
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("- "))
    .map((line) => line.slice(2));
};

export const getContextCompilerOverview = async (): Promise<ContextCompilerOverview> => {
  const repoRoot = resolveRepoRoot();
  const contextRoot = path.join(repoRoot, "aios", "context");
  const compiledPath = path.join(contextRoot, "compiled", "latest.json");
  const receiptPath = path.join(contextRoot, "receipts", "latest.md");
  const [compiledJson, receiptMarkdown, inventory] = await Promise.all([
    readJson(compiledPath),
    readFile(receiptPath, "utf8").catch(() => ""),
    loadInventory(contextRoot),
  ]);
  const compiled = parseCompiledPayload(compiledJson);
  const generatedAt = await stat(compiledPath)
    .then((fileStat) => fileStat.mtime.toISOString())
    .catch(() => null);

  return {
    exists: compiled !== null,
    contextRoot,
    compiledPath,
    receiptPath,
    generatedAt,
    taskSummary: compiled?.task_summary ?? "No compiled context packet found.",
    signals: compiled?.task_classification.signals ?? [],
    domains: compiled?.task_classification.domains ?? [],
    loadedFiles: compiled?.selected_context_files ?? [],
    skippedContext: extractSkippedContext(receiptMarkdown),
    conflicts: compiled?.conflicts ?? [],
    staleContext:
      compiled?.stale_context.map((item) => ({
        id: item.id,
        path: item.path,
        lastReviewed: item.last_reviewed,
      })) ?? [],
    missingContext: compiled?.missing_context ?? [],
    writebackCandidates: compiled?.writeback_candidates ?? [],
    receiptMarkdown: receiptMarkdown || compiled?.context_receipt || "",
    inventory,
  };
};
