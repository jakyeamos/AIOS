#!/usr/bin/env node
// trim-state-files.mjs — enforce append/rotation caps on STATE.md so its
// append-only sections stop growing unbounded.
//
// Usage:
//   node trim-state-files.mjs --check [file-or-dir ...]   report only; exit 1 if any file is over cap
//   node trim-state-files.mjs --write [file-or-dir ...]   trim in place (writes a single .bak alongside)
//
// With no path args it scans ~/projects for canonical files, skipping
// worktrees, shadow-worktrees, and node_modules. A file/dir arg trims just
// that file (or every managed file under that dir) — used by the Stop hook to
// check only the current project.
//
// Only the sections listed in POLICIES are touched. Everything else is left
// byte-for-byte intact. Snapshot sections are meant to be overwritten in place
// by the agent, so they are not listed here — only the log-like sections are.

import fs from "node:fs";
import path from "node:path";
import os from "node:os";

const HOME = os.homedir();

// Per-section rotation policy, keyed by exact "## Heading" text.
const POLICIES = {
  "STATE.md": {
    "Quick Tasks Completed": { type: "table", keep: 12, cellMax: 160 },
    "Current Position": { type: "blocks", keep: 8 },
    "Accumulated Context": { type: "blocks", keep: 8 },
  },
};

// Whole-file soft ceiling (bytes) used only for --check reporting.
const FILE_CEILING = { "STATE.md": 30 * 1024 };

// Any section (covered or not) larger than this gets a generic size cap:
// keep the head paragraph as the snapshot plus the most recent trailing
// paragraphs/blocks that fit. Catches project-specific heading names.
const SECTION_BUDGET = 8 * 1024;

const SKIP =
  /(\/|^)(node_modules|\.worktrees|worktrees|shadow-worktrees|\.aios\/shadow-worktrees|fixtures|audit-worktrees|audit-environments|\.audit-tmp)(\/|$)/;

function truncCell(s, max) {
  if (s.length <= max) return s;
  return s.slice(0, max - 1).replace(/\s+\S*$/, "") + "…";
}

// Split a section body into blocks delimited by lines of only dashes (`---`).
// Falls back to blank-line-separated paragraphs when no dash separators exist.
function splitBlocks(body) {
  const lines = body.split("\n");
  const isSep = (l) => /^-{3,}\s*$/.test(l);
  if (lines.some(isSep)) {
    const blocks = [];
    let cur = [];
    for (const l of lines) {
      if (isSep(l)) {
        blocks.push(cur.join("\n"));
        cur = [];
      } else cur.push(l);
    }
    blocks.push(cur.join("\n"));
    return { blocks, sep: "\n---\n" };
  }
  return { blocks: body.split(/\n\s*\n/), sep: "\n\n" };
}

function trimSection(heading, body, policy) {
  if (policy.type === "table") {
    const lines = body.split("\n");
    const rows = lines.filter((l) => /^\s*\|/.test(l));
    const nonRows = lines.filter((l) => !/^\s*\|/.test(l));
    if (rows.length <= 2) return body; // header + separator only
    const header = rows.slice(0, 2);
    let data = rows.slice(2).filter((r) => r.trim());
    if (data.length > policy.keep) data = data.slice(-policy.keep);
    data = data.map((r) => {
      const cells = r.split("|").map((c, i, arr) =>
        i === 0 || i === arr.length - 1 ? c : truncCell(c.trim(), policy.cellMax),
      );
      return cells.map((c, i, arr) => (i === 0 || i === arr.length - 1 ? c : ` ${c} `)).join("|");
    });
    const preamble = nonRows.filter((l) => l.trim()).join("\n");
    return [preamble, header.join("\n"), data.join("\n")].filter(Boolean).join("\n");
  }

  if (policy.type === "tableTail") {
    // Keep the leading table (truncating its cells) plus the last `keep`
    // trailing note blocks appended after the table.
    const lines = body.split("\n");
    let i = 0;
    const out = [];
    for (; i < lines.length; i++) {
      if (/^\s*\|/.test(lines[i])) {
        out.push(
          lines[i]
            .split("|")
            .map((c, j, arr) =>
              j === 0 || j === arr.length - 1 ? c : ` ${truncCell(c.trim(), policy.cellMax)} `,
            )
            .join("|"),
        );
      } else if (lines[i].trim() === "" && out.length && !/^\s*\|/.test(lines[i + 1] || "|")) {
        break; // table ended
      } else if (out.length && !/^\s*\|/.test(lines[i])) {
        break;
      } else {
        out.push(lines[i]);
      }
    }
    const tail = lines.slice(i).join("\n").trim();
    if (!tail) return out.join("\n");
    const paras = tail.split(/\n\s*\n/).filter((p) => p.trim());
    const kept = paras.slice(-policy.keep);
    return out.join("\n") + "\n\n" + kept.join("\n\n");
  }

  if (policy.type === "bullets") {
    const lines = body.split("\n");
    const bullets = [];
    const other = [];
    for (const l of lines) (/^\s*[-*] /.test(l) ? bullets : other).push(l);
    if (bullets.length <= policy.keep) return body;
    const kept = bullets.slice(0, policy.keep); // convention: newest bullet first
    const lead = other.filter((l) => l.trim()).join("\n");
    return [lead, kept.join("\n")].filter(Boolean).join("\n");
  }

  if (policy.type === "blocks") {
    const { blocks, sep } = splitBlocks(body);
    const head = blocks[0]; // current snapshot header
    let kept = blocks.length > policy.keep + 1 ? blocks.slice(-policy.keep) : blocks.slice(1);
    // Also cap each retained block so a few giant blocks can't defeat the count cap.
    const blockMax = policy.blockMax || 2000;
    const cap = (b) =>
      Buffer.byteLength(b) > blockMax ? truncCell(b, blockMax) + "\n_(truncated)_" : b;
    return [cap(head), ...kept.map(cap)].join(sep);
  }

  return body;
}

// Generic size cap for any section over budget, regardless of heading.
// Assumes append-at-bottom logs: keeps the head paragraph plus the most
// recent trailing paragraphs that fit within budget.
function capBySize(body) {
  if (Buffer.byteLength(body) <= SECTION_BUDGET) return body;
  const { blocks, sep } = splitBlocks(body);
  if (blocks.length <= 1) {
    const paras = body.split(/\n\s*\n/);
    if (paras.length <= 1) return truncCell(body, SECTION_BUDGET) + "\n\n_(truncated for length)_";
    return capJoin(paras, "\n\n");
  }
  return capJoin(blocks, sep);
}

function capJoin(items, sep) {
  const head = items[0];
  const kept = [];
  let used = Buffer.byteLength(head);
  for (let i = items.length - 1; i >= 1; i--) {
    const size = Buffer.byteLength(items[i]) + sep.length;
    if (used + size > SECTION_BUDGET) break;
    kept.unshift(items[i]);
    used += size;
  }
  const dropped = items.length - 1 - kept.length;
  const note = dropped > 0 ? [`_(${dropped} older entries trimmed)_`] : [];
  return [head, ...note, ...kept].join(sep);
}

function processFile(file, { write }) {
  const kind = path.basename(file);
  const policies = POLICIES[kind];
  if (!policies) return null;
  const orig = fs.readFileSync(file, "utf-8");

  // Parse into sections keyed by "## Heading".
  const parts = orig.split(/(?=^## )/m);
  let changed = false;
  const rebuilt = parts
    .map((part) => {
      const m = part.match(/^## (.+?)[ \t]*\n/);
      if (!m) return part;
      const heading = m[1].trim();
      const policy = policies[heading];
      const headerLine = part.slice(0, m[0].length);
      const body = part.slice(m[0].length).replace(/\n+$/, "");
      const trimmed = policy ? trimSection(heading, body, policy) : capBySize(body);
      if (trimmed.trim() === body.trim()) return part;
      changed = true;
      return headerLine + trimmed + "\n\n";
    })
    .join("");

  const before = Buffer.byteLength(orig);
  const after = Buffer.byteLength(rebuilt);
  // Only act on a meaningful reduction. This ignores cosmetic re-spacing and
  // keeps the operation idempotent — a second pass finds nothing to do, so the
  // Stop hook stops nagging once a file has actually been rotated.
  const saved = before - after;
  const meaningful = changed && saved > Math.max(2048, before * 0.05);
  const overCeiling = before > (FILE_CEILING[kind] || Infinity);
  if (write && meaningful) {
    fs.writeFileSync(file + ".bak", orig);
    fs.writeFileSync(file, rebuilt);
  }
  return { file, kind, before, after: meaningful ? after : before, changed: meaningful, overCeiling };
}

function collect(target) {
  const out = [];
  let stat = null;
  try {
    stat = fs.lstatSync(target);
  } catch {
    return out;
  }
  if (stat.isSymbolicLink()) return out;
  if (stat.isFile()) {
    if (!SKIP.test(target) && POLICIES[path.basename(target)]) out.push(target);
    return out;
  }
  const roots = stat?.isDirectory() ? [target] : [];
  const walk = (dir) => {
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const e of entries) {
      if (e.isSymbolicLink()) continue;
      const full = path.join(dir, e.name);
      if (SKIP.test(full)) continue;
      if (e.isDirectory()) walk(full);
      else if (POLICIES[e.name]) out.push(full);
    }
  };
  for (const r of roots) walk(r);
  return out;
}

function main() {
  const args = process.argv.slice(2);
  const write = args.includes("--write");
  const check = args.includes("--check") || !write;
  const paths = args.filter((a) => !a.startsWith("--"));
  const targets = paths.length ? paths : [path.join(HOME, "projects")];

  const files = [...new Set(targets.flatMap(collect))];
  const results = files.map((f) => processFile(f, { write })).filter(Boolean);

  const kb = (b) => (b / 1024).toFixed(1) + "K";
  let over = 0;
  for (const r of results.sort((a, b) => b.before - a.before)) {
    // A file is "over cap" when rotation would still change it — i.e. an
    // unbounded log section exists. That is the actionable enforcement signal.
    const flag = r.changed ? "⚠ " : "  ";
    if (r.changed) {
      over += 1;
      const verb = write ? "→" : "would →";
      const rel = r.file.replace(HOME, "~");
      console.log(`${flag}${kb(r.before)} ${verb} ${kb(r.after)}  ${rel}`);
    }
  }
  const totalBefore = results.reduce((s, r) => s + r.before, 0);
  const totalAfter = results.reduce((s, r) => s + r.after, 0);
  console.log(
    `\n${results.length} managed files | ${kb(totalBefore)} ${write ? "→" : "would →"} ${kb(totalAfter)} (−${kb(totalBefore - totalAfter)})`,
  );
  if (check && !write && over > 0) process.exit(1);
}

main();
