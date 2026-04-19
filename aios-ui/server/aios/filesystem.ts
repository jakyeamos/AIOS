import fs from "node:fs";
import os from "node:os";
import path from "node:path";

type FrontmatterRecord = Record<string, string>;

export const resolveAiosRoot = (): string => {
  const candidates = [process.cwd(), path.resolve(process.cwd(), "..")];

  for (const candidate of candidates) {
    if (fs.existsSync(path.join(candidate, "PROJECT.md"))) {
      return candidate;
    }
  }

  return process.cwd();
};

export const resolveVaultRoot = (): string => {
  const envRoot = process.env.AIOS_VAULT_ROOT;
  const candidates = [
    envRoot ? path.resolve(envRoot.replace(/^~(?=$|\/|\\)/, os.homedir())) : null,
    path.join(os.homedir(), "projects", "Vaults", "Command-Center"),
    path.join(os.homedir(), "Vaults", "Command-Center"),
  ].filter((candidate): candidate is string => Boolean(candidate));

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return path.join(os.homedir(), "projects", "Vaults", "Command-Center");
};

export const parseSimpleFrontmatter = (content: string): FrontmatterRecord => {
  if (!content.startsWith("---\n")) {
    return {};
  }

  const end = content.indexOf("\n---", 4);
  if (end === -1) {
    return {};
  }

  const raw = content.slice(4, end).trim();
  const entries = raw
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.includes(":"))
    .map((line) => {
      const [key, ...rest] = line.split(":");
      return [key.trim(), rest.join(":").trim()] as const;
    });

  return Object.fromEntries(entries);
};

export const parseFrontmatterList = (content: string, key: string): string[] => {
  if (!content.startsWith("---\n")) {
    return [];
  }

  const end = content.indexOf("\n---", 4);
  if (end === -1) {
    return [];
  }

  const frontmatter = content.slice(0, end + 4);
  const matcher = new RegExp(`^${key}:\\s*\\n((?:\\s+-\\s+.+\\n?)*)`, "m");
  const match = frontmatter.match(matcher);

  if (!match?.[1]) {
    return [];
  }

  return match[1]
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("- "))
    .map((line) => line.slice(2).trim());
};

export const stripFrontmatter = (content: string): string => {
  if (!content.startsWith("---\n")) {
    return content;
  }

  const end = content.indexOf("\n---", 4);
  if (end === -1) {
    return content;
  }

  return content.slice(end + 4).trim();
};

export const extractMarkdownTitle = (content: string, fallback: string): string => {
  const match = content.match(/^#\s+(.+)$/m);
  return match?.[1]?.trim() ?? fallback;
};

export const extractSection = (content: string, heading: string): string => {
  const matcher = new RegExp(`^##\\s+${heading}\\s*\\n([\\s\\S]*?)(?=^##\\s+|\\Z)`, "m");
  const match = content.match(matcher);
  return match?.[1]?.trim() ?? "";
};

export const summarizeParagraph = (content: string): string => {
  const stripped = stripFrontmatter(content)
    .replace(/^#\s+.+$/m, "")
    .trim();
  const firstParagraph = stripped.split(/\n\s*\n/)[0] ?? "";
  return firstParagraph.slice(0, 260).trim();
};

export const extractWikiLinks = (content: string): string[] => {
  const matches = content.match(/\[\[([^[\]]+)\]\]/g) ?? [];

  return matches.map((match) =>
    match
      .slice(2, -2)
      .split("|")[0]
      .split("#")[0]
      .trim(),
  );
};
