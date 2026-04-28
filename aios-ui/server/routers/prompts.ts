import fs from "node:fs";
import crypto from "node:crypto";
import path from "node:path";
import { z } from "zod";

import type { Prompt, PromptClassification, PromptTemplate } from "@/lib/types";
import { tableExists } from "@/server/db";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

type PromptRow = {
  id: string;
  sessionId: string;
  promptHash: string | null;
  promptText: string | null;
  classification: string | null;
  outcomeScore: number | null;
  reusableCandidate: number;
  retrievalFired: number;
  retrievalSource: string | null;
};

type PromptTemplateRegistry = {
  templates?: Array<{
    id?: unknown;
    name?: unknown;
    version?: unknown;
    classification?: unknown;
    tags?: unknown;
    purpose?: unknown;
    required_inputs?: unknown;
    optional_inputs?: unknown;
    last_updated?: unknown;
    file?: unknown;
  }>;
};

const getAiosRoot = (): string => {
  return process.env.AIOS_ROOT ?? "/Users/jakyeamos/AIOS";
};

const extractBody = (markdown: string): string => {
  if (!markdown.startsWith("---\n")) {
    return markdown;
  }

  const lines = markdown.split(/\r?\n/);
  const endIndex = lines.findIndex((line, index) => index > 0 && line.trim() === "---");
  if (endIndex === -1) {
    return markdown;
  }

  return lines.slice(endIndex + 1).join("\n").replace(/^\n+/, "");
};

const bodyHash = (markdown: string): string =>
  crypto.createHash("sha256").update(extractBody(markdown), "utf8").digest("hex");

const templateHash = (aiosRoot: string, template: NonNullable<PromptTemplateRegistry["templates"]>[number]): string | null => {
  const templateId = typeof template.id === "string" ? template.id : "";
  const file = typeof template.file === "string" ? template.file : "";
  const candidates = [
    file ? path.join(aiosRoot, file) : "",
    file ? path.join(aiosRoot, "prompts", path.basename(file)) : "",
    templateId ? path.join(aiosRoot, "prompts", `${templateId}.md`) : "",
  ].filter((candidate, index, rows) => candidate.length > 0 && rows.indexOf(candidate) === index);

  const templatePath = candidates.find((candidate) => fs.existsSync(candidate));
  if (!templatePath) {
    return null;
  }

  return bodyHash(fs.readFileSync(templatePath, "utf8"));
};

const stringifyInput = (input: unknown): string => {
  if (typeof input === "string") {
    return input;
  }

  if (input && typeof input === "object" && !Array.isArray(input)) {
    const [key, value] = Object.entries(input as Record<string, unknown>)[0] ?? [];
    if (key && typeof value === "string") {
      return `${key}: ${value}`;
    }
  }

  return "";
};

const listFromUnknown = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map(stringifyInput).filter((item) => item.length > 0);
};

const normalizeClassification = (classification: string | null): PromptClassification => {
  if (classification === "debug") {
    return "debugging";
  }

  if (classification === "plan") {
    return "planning";
  }

  if (
    classification === "debugging" ||
    classification === "planning" ||
    classification === "refactor" ||
    classification === "review" ||
    classification === "explain" ||
    classification === "implement" ||
    classification === "other"
  ) {
    return classification;
  }

  return "other";
};

const mapPrompt = (row: PromptRow): Prompt => ({
  id: row.id,
  sessionId: row.sessionId,
  promptHash: row.promptHash,
  promptText: row.promptText,
  classification: normalizeClassification(row.classification),
  outcomeScore: row.outcomeScore,
  reusableCandidate: row.reusableCandidate === 1,
  retrievalFired: row.retrievalFired === 1,
  retrievalSource: row.retrievalSource,
});

export const promptsRouter = createTRPCRouter({
  templates: publicProcedure.query(({ ctx }): PromptTemplate[] => {
    const aiosRoot = getAiosRoot();
    const registryPath = path.join(aiosRoot, "prompts", "registry.json");
    if (!fs.existsSync(registryPath) || !tableExists("prompt_library_links")) {
      return [];
    }

    const registry = JSON.parse(fs.readFileSync(registryPath, "utf8")) as PromptTemplateRegistry;
    return (registry.templates ?? []).flatMap((template) => {
      const hash = templateHash(aiosRoot, template);
      if (!hash) {
        return [];
      }

      const linked = ctx.db
        .prepare("SELECT 1 FROM prompt_library_links WHERE prompt_hash = ? LIMIT 1")
        .get(hash);
      if (!linked) {
        return [];
      }

      const file = typeof template.file === "string" ? template.file : "";

      return [{
        id: typeof template.id === "string" ? template.id : "unknown",
        name: typeof template.name === "string" ? template.name : "Unnamed template",
        version: typeof template.version === "string" ? template.version : "unknown",
        classification: typeof template.classification === "string" ? template.classification : "other",
        tags: Array.isArray(template.tags) ? template.tags.filter((tag): tag is string => typeof tag === "string") : [],
        purpose: typeof template.purpose === "string" ? template.purpose : "",
        requiredInputs: listFromUnknown(template.required_inputs),
        optionalInputs: listFromUnknown(template.optional_inputs),
        lastUpdated: typeof template.last_updated === "string" ? template.last_updated : "",
        file,
        path: file ? path.join(aiosRoot, file) : registryPath,
      }];
    });
  }),

  list: publicProcedure
    .input(z.object({ limit: z.number().int().min(1).max(200).default(50) }).optional())
    .query(({ ctx, input }): Prompt[] => {
      if (!tableExists("prompts_used") || !tableExists("sessions")) {
        return [];
      }

      const limit = input?.limit ?? 50;
      const rows = ctx.db
        .prepare(
          `
          SELECT
            pu.id,
            pu.session_id AS sessionId,
            pu.prompt_hash AS promptHash,
            pu.prompt_text AS promptText,
            pu.classification,
            pu.outcome_score AS outcomeScore,
            pu.reusable_candidate AS reusableCandidate,
            pu.retrieval_fired AS retrievalFired,
            pu.retrieval_source AS retrievalSource
          FROM prompts_used pu
          INNER JOIN sessions s ON s.id = pu.session_id
          ORDER BY s.started_at DESC
          LIMIT ?
        `,
        )
        .all(limit) as PromptRow[];

      return rows.map(mapPrompt);
    }),

  byHash: publicProcedure
    .input(z.object({ hash: z.string().min(1), limit: z.number().int().min(1).max(200).default(50) }))
    .query(({ ctx, input }): Prompt[] => {
      if (!tableExists("prompts_used") || !tableExists("sessions")) {
        return [];
      }

      const rows = ctx.db
        .prepare(
          `
          SELECT
            pu.id,
            pu.session_id AS sessionId,
            pu.prompt_hash AS promptHash,
            pu.prompt_text AS promptText,
            pu.classification,
            pu.outcome_score AS outcomeScore,
            pu.reusable_candidate AS reusableCandidate,
            pu.retrieval_fired AS retrievalFired,
            pu.retrieval_source AS retrievalSource
          FROM prompts_used pu
          INNER JOIN sessions s ON s.id = pu.session_id
          WHERE pu.prompt_hash = ?
          ORDER BY s.started_at DESC
          LIMIT ?
        `,
        )
        .all(input.hash, input.limit) as PromptRow[];

      return rows.map(mapPrompt);
    }),
});
