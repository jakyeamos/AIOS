#!/usr/bin/env python3
"""
Google Takeout processor for Obsidian vault ingestion.
Converts raw Takeout exports to markdown notes — processes text, discards raw.

Usage:
  python takeout-process.py --takeout /path/to/Takeout --service all
  python takeout-process.py --takeout /path/to/Takeout --service drive
  python takeout-process.py --takeout /path/to/Takeout --service chat

Services: drive, chat, calendar, activity, notebooklm, voice
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

from aios_paths import get_vault_root

DEFAULT_VAULT = get_vault_root()
VAULT = Path(os.environ.get("VAULT") or os.environ.get("AIOS_VAULT_ROOT") or DEFAULT_VAULT)
CORPUS_DIR = "Personal-Corpus"


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-")


# ── DRIVE ─────────────────────────────────────────────────────────────────────


def _pdf_to_text(f: Path) -> str | None:
    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        r = subprocess.run([pdftotext, "-layout", str(f), "-"], capture_output=True)
        if r.returncode == 0:
            return r.stdout.decode("utf-8", errors="replace")
    try:
        import pypdf  # pyright: ignore[reportMissingImports]

        reader = pypdf.PdfReader(str(f))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(p for p in pages if p.strip())
    except Exception:
        return None


def _xlsx_to_md(f: Path) -> str:
    import openpyxl

    wb = openpyxl.load_workbook(str(f), read_only=True, data_only=True)
    parts = []
    for sheet in wb.worksheets:
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            continue
        parts.append(f"## {sheet.title}")
        header, *data_rows = rows
        header = [str(c) if c is not None else "" for c in header]
        parts.append("| " + " | ".join(header) + " |")
        parts.append("| " + " | ".join("---" for _ in header) + " |")
        for row in data_rows:
            cells = [str(c) if c is not None else "" for c in row]
            parts.append("| " + " | ".join(cells) + " |")
        parts.append("")
    return "\n".join(parts)


def _pptx_to_md(f: Path) -> str:
    from pptx import Presentation  # pyright: ignore[reportMissingImports]

    prs = Presentation(str(f))
    parts = []
    for i, slide in enumerate(prs.slides, 1):
        slide_lines = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = para.text.strip()
                    if text:
                        slide_lines.append(text)
        if slide_lines:
            parts.append(f"## Slide {i}")
            parts.extend(slide_lines)
            parts.append("")
    return "\n".join(parts)


def process_drive(takeout: Path, vault: Path) -> None:
    src = takeout / "Google Drive"
    if not src.exists():
        print("  [skip] Google Drive not found")
        return

    out = vault / CORPUS_DIR / "Drive"
    out.mkdir(parents=True, exist_ok=True)

    converted = skipped = 0

    for f in src.rglob("*.docx"):
        if not shutil.which("pandoc"):
            skipped += 1
            continue
        dest = (out / f.relative_to(src)).with_suffix(".md")
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            ["pandoc", str(f), "-t", "markdown", "-o", str(dest)],
            capture_output=True,
        )
        if r.returncode == 0:
            converted += 1
        else:
            skipped += 1

    for f in src.rglob("*.txt"):
        dest = (out / f.relative_to(src)).with_suffix(".md")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
        converted += 1

    for f in src.rglob("*.pdf"):
        text = _pdf_to_text(f)
        if not text or not text.strip():
            skipped += 1
            continue
        dest = (out / f.relative_to(src)).with_suffix(".md")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f"# {f.stem}\n\n{text}", encoding="utf-8")
        converted += 1

    for f in src.rglob("*.xlsx"):
        try:
            md = _xlsx_to_md(f)
        except Exception:
            skipped += 1
            continue
        if not md.strip():
            skipped += 1
            continue
        dest = (out / f.relative_to(src)).with_suffix(".md")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f"# {f.stem}\n\n{md}", encoding="utf-8")
        converted += 1

    for f in src.rglob("*.pptx"):
        try:
            md = _pptx_to_md(f)
        except Exception:
            skipped += 1
            continue
        if not md.strip():
            skipped += 1
            continue
        dest = (out / f.relative_to(src)).with_suffix(".md")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f"# {f.stem}\n\n{md}", encoding="utf-8")
        converted += 1

    print(f"  [drive] {converted} converted, {skipped} skipped")


# ── CHAT ──────────────────────────────────────────────────────────────────────


def process_chat(takeout: Path, vault: Path) -> None:
    src = takeout / "Google Chat"
    if not src.exists():
        print("  [skip] Google Chat not found")
        return

    out = vault / CORPUS_DIR / "Chat"
    out.mkdir(parents=True, exist_ok=True)

    processed = 0

    for mf in src.rglob("messages.json"):
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        messages = data.get("messages", [])
        if not messages:
            continue

        conv_name = mf.parent.name
        dest = out / f"{slugify(conv_name)}.md"

        lines = [f"# {conv_name}", "*Google Chat export*", ""]

        for msg in messages:
            creator = msg.get("creator", {}).get("name", "Unknown")
            text = msg.get("text", "").strip()
            date_str = msg.get("created_date", "")

            if not text:
                continue

            try:
                dt = datetime.strptime(date_str, "%A, %B %d, %Y at %I:%M:%S %p UTC")
                date_fmt = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, AttributeError):
                date_fmt = date_str

            lines += [f"**{creator}** — {date_fmt}", text, ""]

        dest.write_text("\n".join(lines), encoding="utf-8")
        processed += 1

    print(f"  [chat] {processed} conversations exported")


# ── CALENDAR ──────────────────────────────────────────────────────────────────


def process_calendar(takeout: Path, vault: Path) -> None:
    src = takeout / "Calendar"
    if not src.exists():
        print("  [skip] Calendar not found")
        return

    try:
        from icalendar import Calendar
    except ImportError:
        print("  [error] icalendar not installed — run: pip3 install icalendar")
        return

    out = vault / CORPUS_DIR / "Calendar"
    out.mkdir(parents=True, exist_ok=True)

    events_by_year: dict[int, list[dict]] = {}

    for ics in src.rglob("*.ics"):
        try:
            cal = Calendar.from_ical(ics.read_bytes())
        except Exception:
            continue

        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            summary = str(component.get("SUMMARY", "Untitled"))
            dtstart = component.get("DTSTART")
            description = str(component.get("DESCRIPTION", "")).strip()
            location = str(component.get("LOCATION", "")).strip()

            if not dtstart:
                continue

            dt = dtstart.dt
            if not hasattr(dt, "year"):
                continue

            year = dt.year
            date_str = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)
            events_by_year.setdefault(year, []).append(
                {
                    "date": date_str,
                    "summary": summary,
                    "description": description,
                    "location": location,
                }
            )

    for year, events in sorted(events_by_year.items()):
        events.sort(key=lambda e: e["date"])
        lines = [f"# Calendar {year}", ""]
        for e in events:
            lines.append(f"## {e['date']} — {e['summary']}")
            if e["location"]:
                lines.append(f"*{e['location']}*")
            if e["description"]:
                lines += ["", e["description"]]
            lines.append("")
        (out / f"{year}.md").write_text("\n".join(lines), encoding="utf-8")

    total = sum(len(v) for v in events_by_year.values())
    print(f"  [calendar] {total} events across {len(events_by_year)} years")


# ── ACTIVITY ──────────────────────────────────────────────────────────────────


def process_activity(takeout: Path, vault: Path) -> None:
    src = takeout / "My Activity"
    if not src.exists():
        print("  [skip] My Activity not found")
        return

    out = vault / CORPUS_DIR / "Activity"
    out.mkdir(parents=True, exist_ok=True)

    search_file = src / "Search" / "MyActivity.json"
    if not search_file.exists():
        print("  [activity] MyActivity.json not found under Search/")
        return

    try:
        data = json.loads(search_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("  [activity] Could not parse MyActivity.json")
        return

    by_month: dict[str, list[str]] = {}

    for item in data:
        title = item.get("title", "")
        query = re.sub(r"^Searched for\s+", "", title).strip()
        if not query:
            continue

        time_str = item.get("time", "")
        try:
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            month_key = dt.strftime("%Y-%m")
        except (ValueError, AttributeError):
            month_key = "unknown"

        by_month.setdefault(month_key, []).append(query)

    for month_key, queries in sorted(by_month.items()):
        lines = [f"# Search Activity — {month_key}", ""] + [f"- {q}" for q in queries] + [""]
        (out / f"search-{month_key}.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"  [activity] {len(data)} queries across {len(by_month)} months")


# ── NOTEBOOKLM ────────────────────────────────────────────────────────────────


def process_notebooklm(takeout: Path, vault: Path) -> None:
    src = takeout / "NotebookLM"
    if not src.exists():
        print("  [skip] NotebookLM not found")
        return

    out = vault / CORPUS_DIR / "NotebookLM"
    out.mkdir(parents=True, exist_ok=True)

    copied = 0
    for f in src.rglob("*"):
        if f.is_file():
            dest = out / f.relative_to(src)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            copied += 1

    print(f"  [notebooklm] {copied} files copied")


# ── VOICE ─────────────────────────────────────────────────────────────────────


class _TranscriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._capture = False

    def handle_starttag(self, tag, attrs):
        if dict(attrs).get("class") in ("fn", "full-text"):
            self._capture = True

    def handle_data(self, data):
        if self._capture and data.strip():
            self.parts.append(data.strip())

    def handle_endtag(self, tag):
        self._capture = False


def process_voice(takeout: Path, vault: Path) -> None:
    src = takeout / "Google Voice"
    if not src.exists():
        print("  [skip] Google Voice not found")
        return

    out = vault / CORPUS_DIR / "Voice"
    out.mkdir(parents=True, exist_ok=True)

    processed = 0
    for html_file in src.rglob("*.html"):
        parser = _TranscriptParser()
        try:
            parser.feed(html_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        text = " ".join(parser.parts)
        if not text:
            continue

        (out / f"{html_file.stem}.md").write_text(
            f"# {html_file.stem}\n\n{text}\n", encoding="utf-8"
        )
        processed += 1

    print(f"  [voice] {processed} transcripts extracted")


# ── MAIN ──────────────────────────────────────────────────────────────────────

SERVICES = {
    "drive": process_drive,
    "chat": process_chat,
    "calendar": process_calendar,
    "activity": process_activity,
    "notebooklm": process_notebooklm,
    "voice": process_voice,
}


def main():
    parser = argparse.ArgumentParser(description="Google Takeout → Obsidian vault")
    parser.add_argument("--takeout", required=True, help="Path to extracted Takeout directory")
    parser.add_argument(
        "--vault",
        default=str(VAULT),
        help=f"Obsidian vault root (default: {DEFAULT_VAULT})",
    )
    parser.add_argument(
        "--service",
        default="all",
        choices=list(SERVICES.keys()) + ["all"],
    )
    args = parser.parse_args()

    takeout_dir = Path(args.takeout).expanduser().resolve()
    vault_dir = Path(args.vault).expanduser().resolve()

    if not takeout_dir.exists():
        print(f"Error: {takeout_dir} does not exist")
        sys.exit(1)

    print(f"Takeout : {takeout_dir}")
    print(f"Vault   : {vault_dir / CORPUS_DIR}")
    print()

    targets = (
        SERVICES.items() if args.service == "all" else [(args.service, SERVICES[args.service])]
    )
    for name, fn in targets:
        print(f"Processing {name}...")
        fn(takeout_dir, vault_dir)

    print("\nDone. Safe to delete the raw export.")


if __name__ == "__main__":
    main()
