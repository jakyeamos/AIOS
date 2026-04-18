import fs from "node:fs";
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
