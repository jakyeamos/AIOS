# AI History Import/Archive — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local-first, script-driven pipeline that imports ChatGPT exports, Claude export-bundle conversations, and Codex local session rollouts into a scoped archive area of the Obsidian vault, with staged review and SQLite-backed batch tracking.

**Architecture:** Python CLI (`import-ai-history.py`) parses source-specific JSON/JSONL into normalized conversation dicts, renders them as markdown notes with `type: ai-history` frontmatter, and stages them outside the vault. ChatGPT remains a JSON-array export, Claude is a `conversations.json` export-bundle file with `chat_messages`, and Codex is a local JSONL rollout/session format under `~/.codex`. Two shell scripts — `review-imports.sh` (read-only stats plus aggregate pattern analysis across `keep` and `deferred`) and `promote-imports.sh` (vault promotion + batch synthesis scaffold, with optional `--include-deferred`) — gate promotion. SQLite tracks import metadata; full conversation content lives in markdown only.

**Tech Stack:** Python 3.11+, SQLite (via `sqlite3` stdlib), bash, Obsidian (Dataview plugin for vault), existing `~/AIOS/data/aios.db`.

**Spec:** `~/AIOS/docs/specs/2026-04-01-ai-history-import-design.md`  
**Phase scope:** Phase 1 (infrastructure, ChatGPT parser, review/promote scripts) + Phase 2 (Claude + Codex format support, quality scoring, deduplication, health check). Phase 3 (`resurface.sh`) is out of scope for this plan. As of 2026-04-02, all Phase 1 and Phase 2 implementation work is complete except the real ChatGPT import run, which remains blocked by missing export data.

## Implementation Status (2026-04-02)

- Completed: Tasks 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 13
- Partially complete: Task 12 (`make_id` coverage and live Claude dedup rerun are done; the real ChatGPT rerun remains blocked with Task 7)
- Blocked: Task 7 until a real ChatGPT export is available
- Actual execution order used: `6 -> 8 -> 9 -> 12 -> 10 -> 11 -> 13`, with Task 7 deferred by missing data
- Live batches completed:
  - `20260402033854--claude`: 145 total, 59 promoted, 86 deferred
  - `20260402034120--codex`: 314 total, 57 promoted, 257 deferred
- Deferred policy was refined during implementation: `deferred` now means "thin individually," not "discarded." Deferred notes remain staged, are included in batch-level pattern analysis, and can be promoted explicitly with `promote-imports.sh --include-deferred`.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `~/Vaults/Command-Center/01 Dashboard/Open Actions.md` | Modify | Exclude `09 Archive` from whole-vault query |
| `~/Vaults/Command-Center/09 Archive/AI History/_Index.md` | Create | Coverage table + batch links |
| `~/Vaults/Command-Center/09 Archive/AI History/ChatGPT/` | Create dir | Yearly subfolders for ChatGPT imports |
| `~/Vaults/Command-Center/09 Archive/AI History/Claude/` | Create dir | Yearly subfolders for Claude imports |
| `~/Vaults/Command-Center/09 Archive/AI History/Codex/` | Create dir | Yearly subfolders for Codex imports |
| `~/AIOS/staging/ai-history/raw/` | Create dir | Raw export JSON/JSONL files and preserved export bundle snapshots (permanent) |
| `~/AIOS/staging/ai-history/ready/` | Create dir | Transformed markdown before vault promotion |
| `~/AIOS/bin/migrate-add-ai-history.sh` | Create | One-time SQLite migration |
| `~/AIOS/tests/fixtures/chatgpt_sample.json` | Create | 2-conversation ChatGPT export fixture |
| `~/AIOS/tests/fixtures/claude_sample.json` | Create | 1-conversation Claude fixture using real `chat_messages` + `content[]` shape |
| `~/AIOS/tests/fixtures/codex_sample.json` | Create | Representative normalized Codex session fixture derived from JSONL rollout events |
| `~/AIOS/tests/test_import_ai_history.py` | Create | Unit tests for parser, transformer, quality scoring |
| `~/AIOS/bin/import-ai-history.py` | Create | Main import pipeline (parse + render + SQLite write) |
| `~/AIOS/bin/review-imports.sh` | Create | Read-only batch stats from SQLite |
| `~/AIOS/bin/promote-imports.sh` | Create | Vault promotion + batch synthesis note scaffold |
| `~/ai-os/scripts/health_check.sh` | Modify | Add import stats block |

---

### Task 1: Fix Open Actions Dashboard [Completed 2026-04-01]

**Files:**
- Modify: `~/Vaults/Command-Center/01 Dashboard/Open Actions.md`

- [ ] **Step 1: Read the current file**

```bash
cat ~/Vaults/Command-Center/"01 Dashboard/Open Actions.md"
```

- [ ] **Step 2: Update the FROM clause**

Open `~/Vaults/Command-Center/01 Dashboard/Open Actions.md`. Change the dataview block from:

```
FROM ""
WHERE type = "next-action" AND status != "done"
```

to:

```
FROM "" AND -"09 Archive"
WHERE type = "next-action" AND status != "done"
```

The full file should read:

```markdown
---
type: dashboard
tags: [dashboard]
---

# Open Next Actions

```dataview
TABLE project, priority, due, context
FROM "" AND -"09 Archive"
WHERE type = "next-action" AND status != "done"
SORT priority DESC, due ASC
```
```

- [ ] **Step 3: Verify in Obsidian**

Open the vault in Obsidian and navigate to `01 Dashboard/Open Actions`. Confirm the query still shows your existing next-action notes and does not error.

---

### Task 2: Create Vault Folder Structure [Completed 2026-04-01]

**Files:**
- Create: `~/Vaults/Command-Center/09 Archive/AI History/ChatGPT/` (dir)
- Create: `~/Vaults/Command-Center/09 Archive/AI History/Claude/` (dir)
- Create: `~/Vaults/Command-Center/09 Archive/AI History/Codex/` (dir)
- Create: `~/Vaults/Command-Center/09 Archive/AI History/_Index.md`

- [ ] **Step 1: Create directories**

```bash
mkdir -p ~/Vaults/Command-Center/"09 Archive/AI History/ChatGPT"
mkdir -p ~/Vaults/Command-Center/"09 Archive/AI History/Claude"
mkdir -p ~/Vaults/Command-Center/"09 Archive/AI History/Codex"
```

- [ ] **Step 2: Create `_Index.md`**

Write `~/Vaults/Command-Center/09 Archive/AI History/_Index.md`:

```markdown
---
type: archive-index
updated: 2026-04-01
---

# AI History Archive

## Coverage

| Source | Date Range | Count |
|--------|------------|-------|

## Import Batches

<!-- Links to _Batch-{id}.md notes will be added here after each promote run -->

## Notes

<!-- Themes, notable clusters, what's worth retrieving -->
```

- [ ] **Step 3: Verify**

```bash
ls ~/Vaults/Command-Center/"09 Archive/AI History/"
```

Expected output:
```
ChatGPT/   Claude/   Codex/   _Index.md
```

---

### Task 3: Staging Directories + SQLite Migration [Completed 2026-04-01]

**Files:**
- Create: `~/AIOS/staging/ai-history/raw/` (dir)
- Create: `~/AIOS/staging/ai-history/ready/` (dir)
- Create: `~/AIOS/bin/migrate-add-ai-history.sh`

- [ ] **Step 1: Create staging directories**

```bash
mkdir -p ~/AIOS/staging/ai-history/raw
mkdir -p ~/AIOS/staging/ai-history/ready
```

- [ ] **Step 2: Write the migration script**

Write `~/AIOS/bin/migrate-add-ai-history.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
DB=~/AIOS/data/aios.db

sqlite3 "$DB" <<'SQL'
CREATE TABLE IF NOT EXISTS ai_history_imports (
  id                TEXT PRIMARY KEY,
  batch_id          TEXT NOT NULL,
  source            TEXT NOT NULL,
  source_id         TEXT,
  model             TEXT,
  conversation_date TEXT NOT NULL,
  title             TEXT NOT NULL,
  slug              TEXT NOT NULL,
  topic_tags        TEXT NOT NULL DEFAULT '[]',
  vault_path        TEXT,
  quality           TEXT DEFAULT 'keep',
  status            TEXT DEFAULT 'staged',
  promoted_at       TEXT,
  created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_imports_batch  ON ai_history_imports(batch_id);
CREATE INDEX IF NOT EXISTS idx_imports_status ON ai_history_imports(status);
CREATE INDEX IF NOT EXISTS idx_imports_source ON ai_history_imports(source);
CREATE INDEX IF NOT EXISTS idx_imports_date   ON ai_history_imports(conversation_date);
SQL

echo "Migration complete. Table ai_history_imports ready in $DB"
```

- [ ] **Step 3: Run the migration**

```bash
chmod +x ~/AIOS/bin/migrate-add-ai-history.sh
~/AIOS/bin/migrate-add-ai-history.sh
```

Expected:
```
Migration complete. Table ai_history_imports ready in /Users/jakyeamos/AIOS/data/aios.db
```

- [ ] **Step 4: Verify the table exists**

```bash
sqlite3 ~/AIOS/data/aios.db ".tables" | tr ' ' '\n' | grep ai_history
```

Expected:
```
ai_history_imports
```

---

### Task 4: Test Fixtures + Test Skeleton [Completed 2026-04-01]

**Files:**
- Create: `~/AIOS/tests/fixtures/chatgpt_sample.json`
- Create: `~/AIOS/tests/fixtures/claude_sample.json`
- Create: `~/AIOS/tests/test_import_ai_history.py`

- [ ] **Step 0: Ensure `pytest` is available**

```bash
python3 -m pytest --version >/dev/null 2>&1 || python3 -m pip install pytest
```

- [ ] **Step 1: Write the ChatGPT fixture**

Write `~/AIOS/tests/fixtures/chatgpt_sample.json`:

```json
[
  {
    "title": "Context Windows and Retrieval",
    "create_time": 1710460800.0,
    "update_time": 1710464400.0,
    "id": "conv-aaa",
    "conversation_id": "conv-aaa",
    "mapping": {
      "node-sys": {
        "id": "node-sys",
        "message": {
          "id": "node-sys",
          "author": {"role": "system"},
          "content": {"content_type": "text", "parts": [""]},
          "create_time": 1710460800.0
        },
        "parent": null,
        "children": ["node-u1"]
      },
      "node-u1": {
        "id": "node-u1",
        "message": {
          "id": "node-u1",
          "author": {"role": "user"},
          "content": {"content_type": "text", "parts": ["How do context windows affect retrieval quality in RAG systems?"]},
          "create_time": 1710460801.0
        },
        "parent": "node-sys",
        "children": ["node-a1"]
      },
      "node-a1": {
        "id": "node-a1",
        "message": {
          "id": "node-a1",
          "author": {"role": "assistant"},
          "content": {"content_type": "text", "parts": ["Context windows have a significant impact on retrieval quality in RAG systems. When the context window is too small you cannot fit enough retrieved chunks to give the model sufficient information to synthesize a good answer. When it is too large the model may lose focus on the most relevant parts of the retrieved context. The sweet spot depends on the density of your documents and the nature of the queries. For most production RAG systems a 4k to 8k context window works well with chunk sizes around 512 tokens and top-k retrieval of 5 to 10 chunks."]},
          "create_time": 1710460802.0
        },
        "parent": "node-u1",
        "children": ["node-u2"]
      },
      "node-u2": {
        "id": "node-u2",
        "message": {
          "id": "node-u2",
          "author": {"role": "user"},
          "content": {"content_type": "text", "parts": ["What happens when the retrieved context contradicts the model's training?"]},
          "create_time": 1710460803.0
        },
        "parent": "node-a1",
        "children": ["node-a2"]
      },
      "node-a2": {
        "id": "node-a2",
        "message": {
          "id": "node-a2",
          "author": {"role": "assistant"},
          "content": {"content_type": "text", "parts": ["This is called retrieval-training conflict and it is one of the harder problems in RAG. Models generally follow retrieved context over parametric knowledge when the retrieved text is authoritative and clearly stated. But when the conflict is subtle or the retrieved text is ambiguous the model may hallucinate a blend of both sources. The best mitigations are to use explicit instruction framing like answer only from the provided context and to include confidence signaling in your retrieval pipeline so the model knows when evidence is weak."]},
          "create_time": 1710460804.0
        },
        "parent": "node-u2",
        "children": []
      }
    }
  },
  {
    "title": "Hi",
    "create_time": 1710460900.0,
    "update_time": 1710460901.0,
    "id": "conv-bbb",
    "conversation_id": "conv-bbb",
    "mapping": {
      "node-u1": {
        "id": "node-u1",
        "message": {
          "id": "node-u1",
          "author": {"role": "user"},
          "content": {"content_type": "text", "parts": ["Hi"]},
          "create_time": 1710460900.0
        },
        "parent": null,
        "children": ["node-a1"]
      },
      "node-a1": {
        "id": "node-a1",
        "message": {
          "id": "node-a1",
          "author": {"role": "assistant"},
          "content": {"content_type": "text", "parts": ["Hello! How can I help?"]},
          "create_time": 1710460901.0
        },
        "parent": "node-u1",
        "children": []
      }
    }
  }
]
```

- [ ] **Step 2: Write the Claude fixture**

Write `~/AIOS/tests/fixtures/claude_sample.json`:

```json
[
  {
    "uuid": "claude-conv-aaa",
    "name": "Soundscape Architecture Discussion",
    "summary": "",
    "created_at": "2025-01-10T15:30:00.000000+00:00",
    "updated_at": "2025-01-10T16:00:00.000000+00:00",
    "account": {"uuid": "user-uuid"},
    "chat_messages": [
      {
        "uuid": "msg-1",
        "text": "I am building a music social platform and need to decide whether to use event sourcing or a traditional CRUD model for the feed.",
        "content": [
          {
            "start_timestamp": "2025-01-10T15:30:00.000000+00:00",
            "stop_timestamp": "2025-01-10T15:30:00.000000+00:00",
            "flags": null,
            "type": "text",
            "text": "I am building a music social platform and need to decide whether to use event sourcing or a traditional CRUD model for the feed.",
            "citations": []
          }
        ],
        "sender": "human",
        "created_at": "2025-01-10T15:30:00.000000+00:00",
        "updated_at": "2025-01-10T15:30:00.000000+00:00",
        "attachments": [],
        "files": [{"file_name": "architecture-diagram.png"}]
      },
      {
        "uuid": "msg-2",
        "text": "",
        "content": [
          {
            "start_timestamp": "2025-01-10T15:31:00.000000+00:00",
            "stop_timestamp": "2025-01-10T15:31:01.000000+00:00",
            "flags": null,
            "type": "thinking",
            "thinking": "Comparing event sourcing and CRUD tradeoffs for a feed system.",
            "summaries": [{"summary": "Comparing architecture tradeoffs"}],
            "cut_off": false,
            "truncated": false,
            "alternative_display_type": null,
            "signature": null
          },
          {
            "start_timestamp": "2025-01-10T15:31:01.000000+00:00",
            "stop_timestamp": "2025-01-10T15:31:02.000000+00:00",
            "flags": null,
            "type": "text",
            "text": "For a music social feed the tradeoffs break down like this. Event sourcing gives you an immutable audit log and makes it easy to rebuild materialized views when your feed algorithm changes. The downside is operational complexity: you need a projection layer and your reads become eventually consistent. CRUD is simpler to start with and easier to reason about for a small team.",
            "citations": []
          },
          {
            "start_timestamp": "2025-01-10T15:31:02.000000+00:00",
            "stop_timestamp": "2025-01-10T15:31:02.500000+00:00",
            "flags": null,
            "type": "tool_use",
            "id": null,
            "name": "web_search",
            "input": {"query": "event sourcing feed architecture tradeoffs"},
            "message": "Searching the web",
            "integration_name": null,
            "integration_icon_url": null,
            "icon_name": null,
            "context": null,
            "display_content": null,
            "approval_options": null,
            "approval_key": null,
            "is_mcp_app": null,
            "mcp_server_url": null
          },
          {
            "start_timestamp": null,
            "stop_timestamp": null,
            "flags": null,
            "type": "tool_result",
            "tool_use_id": null,
            "name": "web_search",
            "content": [
              {
                "type": "knowledge",
                "title": "Event Sourcing Overview",
                "url": "https://example.com/event-sourcing",
                "text": "Event sourcing keeps an append-only record of changes.",
                "is_citable": true
              }
            ]
          },
          {
            "start_timestamp": null,
            "stop_timestamp": null,
            "flags": null,
            "type": "token_budget"
          }
        ],
        "sender": "assistant",
        "created_at": "2025-01-10T15:31:00.000000+00:00",
        "updated_at": "2025-01-10T15:31:00.000000+00:00",
        "attachments": [
          {
            "file_name": "decision-notes.html",
            "file_size": 1024,
            "file_type": "text/html",
            "extracted_content": "<html><body><p>Architecture notes</p></body></html>"
          }
        ],
        "files": []
      },
      {
        "uuid": "msg-3",
        "text": "What about the real-time aspects? We need listeners to see new tracks as they are posted.",
        "content": [
          {
            "start_timestamp": "2025-01-10T15:32:00.000000+00:00",
            "stop_timestamp": "2025-01-10T15:32:00.000000+00:00",
            "flags": null,
            "type": "text",
            "text": "What about the real-time aspects? We need listeners to see new tracks as they are posted.",
            "citations": []
          }
        ],
        "sender": "human",
        "created_at": "2025-01-10T15:32:00.000000+00:00",
        "updated_at": "2025-01-10T15:32:00.000000+00:00",
        "attachments": [],
        "files": []
      },
      {
        "uuid": "msg-4",
        "text": "For real-time delivery the architecture choice is separate from CRUD versus event sourcing. You want a pub-sub layer. The simplest path is Postgres LISTEN/NOTIFY or a Redis pub-sub channel that your API server subscribes to.",
        "content": [
          {
            "start_timestamp": "2025-01-10T15:33:00.000000+00:00",
            "stop_timestamp": "2025-01-10T15:33:00.000000+00:00",
            "flags": null,
            "type": "text",
            "text": "For real-time delivery the architecture choice is separate from CRUD versus event sourcing. You want a pub-sub layer. The simplest path is Postgres LISTEN/NOTIFY or a Redis pub-sub channel that your API server subscribes to.",
            "citations": []
          }
        ],
        "sender": "assistant",
        "created_at": "2025-01-10T15:33:00.000000+00:00",
        "updated_at": "2025-01-10T15:33:00.000000+00:00",
        "attachments": [],
        "files": []
      }
    ]
  }
]
```

- [ ] **Step 3: Write the test skeleton**

Write `~/AIOS/tests/test_import_ai_history.py`:

```python
"""
Tests for import-ai-history.py

Run from ~/AIOS/:
    python3 -m pytest tests/test_import_ai_history.py -v

The module under test lives at ~/AIOS/bin/import_ai_history.py
(import-ai-history.py is renamed to import_ai_history.py for importability).
"""

import json
import sys
import os
from pathlib import Path

# Allow importing from ~/AIOS/bin/
sys.path.insert(0, str(Path.home() / "AIOS/bin"))

import pytest

FIXTURES = Path.home() / "AIOS/tests/fixtures"


@pytest.fixture
def chatgpt_sample():
    with open(FIXTURES / "chatgpt_sample.json") as f:
        return json.load(f)


@pytest.fixture
def claude_sample():
    with open(FIXTURES / "claude_sample.json") as f:
        return json.load(f)


@pytest.fixture
def chatgpt_substantive(chatgpt_sample):
    """The first conversation — has 2 full exchanges, should be 'keep'."""
    return chatgpt_sample[0]


@pytest.fixture
def chatgpt_trivial(chatgpt_sample):
    """The second conversation — single exchange, should be 'deferred'."""
    return chatgpt_sample[1]


# --- title_to_slug ---

def test_slug_basic():
    from import_ai_history import title_to_slug
    assert title_to_slug("Context Windows and Retrieval Tradeoffs") == "context-windows-and-retrieval"


def test_slug_limits_to_6_words():
    from import_ai_history import title_to_slug
    result = title_to_slug("one two three four five six seven eight")
    assert result == "one-two-three-four-five-six"


def test_slug_strips_special_characters():
    from import_ai_history import title_to_slug
    assert title_to_slug("How do I fix this? (Part 2)") == "how-do-i-fix-this-part"


def test_slug_no_leading_trailing_hyphens():
    from import_ai_history import title_to_slug
    result = title_to_slug("  Hello World  ")
    assert not result.startswith("-")
    assert not result.endswith("-")


# --- make_id ---

def test_id_is_deterministic():
    from import_ai_history import make_id
    assert make_id("chatgpt", "conv-123", "2024-01-01", "Test") == make_id("chatgpt", "conv-123", "2024-01-01", "Test")


def test_id_differs_by_source():
    from import_ai_history import make_id
    assert make_id("chatgpt", "conv-123", "2024-01-01", "Test") != make_id("claude", "conv-123", "2024-01-01", "Test")


def test_id_is_12_chars():
    from import_ai_history import make_id
    assert len(make_id("chatgpt", "conv-123", "2024-01-01", "Test")) == 12


def test_id_differs_by_source_native_id():
    from import_ai_history import make_id
    assert make_id("chatgpt", "conv-aaa", "2024-01-01", "Test") != make_id("chatgpt", "conv-bbb", "2024-01-01", "Test")


def test_extract_tags_uses_first_exchange_signal():
    from import_ai_history import extract_tags
    exchanges = [
        {
            "question": "How does React streaming work in Next.js?",
            "answer": "React server rendering in Next.js can stream chunks progressively.",
        }
    ]
    tags = extract_tags("chatgpt", "Hi", exchanges)
    assert "topic/react" in tags
    assert "topic/nextjs" in tags


# --- score_quality ---

def test_quality_keep_sufficient_exchanges_and_words():
    from import_ai_history import score_quality
    exchanges = [
        {"question": "How does X work?", "answer": "X works by " + "word " * 55},
        {"question": "What about Y?",    "answer": "Y is different because " + "word " * 55},
    ]
    assert score_quality(exchanges) == "keep"


def test_quality_deferred_single_exchange():
    from import_ai_history import score_quality
    exchanges = [{"question": "Hi", "answer": "Hello there " * 20}]
    assert score_quality(exchanges) == "deferred"


def test_quality_deferred_short_answers():
    from import_ai_history import score_quality
    exchanges = [
        {"question": "A?", "answer": "Yes."},
        {"question": "B?", "answer": "No."},
        {"question": "C?", "answer": "Maybe."},
    ]
    assert score_quality(exchanges) == "deferred"


# --- parse_chatgpt_messages ---

def test_chatgpt_messages_ordered_by_time():
    from import_ai_history import parse_chatgpt_messages
    mapping = {
        "n1": {"message": {"author": {"role": "user"},      "content": {"parts": ["First"]},    "create_time": 1.0}},
        "n2": {"message": {"author": {"role": "assistant"}, "content": {"parts": ["Response"]}, "create_time": 2.0}},
        "n3": {"message": {"author": {"role": "user"},      "content": {"parts": ["Second"]},   "create_time": 3.0}},
    }
    msgs = parse_chatgpt_messages(mapping)
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    assert msgs[0]["text"] == "First"


def test_chatgpt_messages_skips_system_and_empty():
    from import_ai_history import parse_chatgpt_messages
    mapping = {
        "sys": {"message": {"author": {"role": "system"},    "content": {"parts": [""]},  "create_time": 0.0}},
        "u1":  {"message": {"author": {"role": "user"},      "content": {"parts": ["Q"]}, "create_time": 1.0}},
    }
    msgs = parse_chatgpt_messages(mapping)
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"


# --- messages_to_exchanges ---

def test_messages_to_exchanges_pairs_correctly():
    from import_ai_history import messages_to_exchanges
    messages = [
        {"role": "user",      "text": "Q1", "time": 1},
        {"role": "assistant", "text": "A1", "time": 2},
        {"role": "user",      "text": "Q2", "time": 3},
        {"role": "assistant", "text": "A2", "time": 4},
    ]
    exchanges = messages_to_exchanges(messages)
    assert len(exchanges) == 2
    assert exchanges[0] == {"question": "Q1", "answer": "A1"}
    assert exchanges[1] == {"question": "Q2", "answer": "A2"}


def test_messages_to_exchanges_joins_consecutive_assistant_messages():
    from import_ai_history import messages_to_exchanges
    messages = [
        {"role": "user", "text": "Q1", "time": 1},
        {"role": "assistant", "text": "A1 part 1", "time": 2},
        {"role": "assistant", "text": "A1 part 2", "time": 3},
        {"role": "user", "text": "Q2", "time": 4},
    ]
    exchanges = messages_to_exchanges(messages)
    assert exchanges[0]["answer"] == "A1 part 1\n\nA1 part 2"


# --- parse_chatgpt_conversation ---

def test_chatgpt_parse_structure(chatgpt_substantive):
    from import_ai_history import parse_chatgpt_conversation
    conv = parse_chatgpt_conversation(chatgpt_substantive, "test-batch")
    assert conv["source"] == "chatgpt"
    assert conv["date"] == "2024-03-15"
    assert conv["title"] == "Context Windows and Retrieval"
    assert conv["batch_id"] == "test-batch"
    assert "ai-history/chatgpt" in conv["tags"]
    assert len(conv["key_exchanges"]) > 0
    assert len(conv["slug"]) > 0


def test_chatgpt_substantive_is_keep(chatgpt_substantive):
    from import_ai_history import parse_chatgpt_conversation
    conv = parse_chatgpt_conversation(chatgpt_substantive, "test-batch")
    assert conv["quality"] == "keep"


def test_chatgpt_trivial_is_deferred(chatgpt_trivial):
    from import_ai_history import parse_chatgpt_conversation
    conv = parse_chatgpt_conversation(chatgpt_trivial, "test-batch")
    assert conv["quality"] == "deferred"


# --- parse_claude_conversation ---

def test_claude_parse_structure(claude_sample):
    from import_ai_history import parse_claude_conversation
    conv = parse_claude_conversation(claude_sample[0], "test-batch")
    assert conv["source"] == "claude"
    assert conv["date"] == "2025-01-10"
    assert conv["title"] == "Soundscape Architecture Discussion"
    assert "ai-history/claude" in conv["tags"]
    assert conv["quality"] == "keep"


def test_claude_parse_uses_content_text_when_top_level_text_is_blank(claude_sample):
    from import_ai_history import parse_claude_conversation
    conv = parse_claude_conversation(claude_sample[0], "test-batch")
    joined_answers = "\n".join(ex["answer"] for ex in conv["key_exchanges"])
    assert "tradeoffs break down like this" in joined_answers


def test_claude_parse_ignores_non_text_content_parts(claude_sample):
    from import_ai_history import parse_claude_conversation
    conv = parse_claude_conversation(claude_sample[0], "test-batch")
    summary = conv["summary"].lower()
    assert "thinking" not in summary
    assert "web_search" not in summary


# --- render_markdown ---

def test_markdown_has_required_sections(chatgpt_substantive):
    from import_ai_history import parse_chatgpt_conversation, render_markdown
    conv = parse_chatgpt_conversation(chatgpt_substantive, "test-batch")
    md = render_markdown(conv)
    for section in ("type: ai-history", "## Summary", "## Why This Mattered",
                     "## Key Exchanges", "## Notes"):
        assert section in md, f"Missing section: {section}"


def test_markdown_no_forbidden_frontmatter_fields(chatgpt_substantive):
    from import_ai_history import parse_chatgpt_conversation, render_markdown
    conv = parse_chatgpt_conversation(chatgpt_substantive, "test-batch")
    md = render_markdown(conv)
    for field in ("status:", "project:", "priority:", "due:", "outcome_score:", "reusable_candidate:"):
        assert field not in md, f"Forbidden frontmatter field found: {field}"


def test_markdown_type_is_ai_history(chatgpt_substantive):
    from import_ai_history import parse_chatgpt_conversation, render_markdown
    conv = parse_chatgpt_conversation(chatgpt_substantive, "test-batch")
    md = render_markdown(conv)
    assert "type: ai-history" in md
    # must not accidentally have other types
    assert "type: session" not in md
    assert "type: project" not in md
```

- [ ] **Step 4: Run tests — expect ImportError (module does not exist yet)**

```bash
cd ~/AIOS && python3 -m pytest tests/test_import_ai_history.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'import_ai_history'` — confirms tests are wired and waiting for implementation.

---

### Task 5: Core Import Module — Parsing and Rendering [Completed 2026-04-01]

**Files:**
- Create: `~/AIOS/bin/import_ai_history.py`

- [ ] **Step 1: Write the module**

Write `~/AIOS/bin/import_ai_history.py`:

```python
"""
AIOS: AI History Import — core module
Parses ChatGPT exports, Claude `conversations.json` exports, and Codex
session rollouts into normalized conversation dicts.
Renders conversation dicts as Obsidian markdown notes.

This module is imported by tests and called by the CLI (import-ai-history.py).
"""

import hashlib
import re
from datetime import datetime, timezone


# --- Configuration ---

MIN_EXCHANGE_COUNT = 2    # minimum complete Q&A pairs to qualify as 'keep'
MIN_ASSISTANT_WORDS = 100 # minimum total words across all assistant responses for 'keep'

TOPIC_MAP = {
    "context": "topic/context-management",
    "retrieval": "topic/retrieval",
    "rag": "topic/rag",
    "embed": "topic/embeddings",
    "prompt": "topic/prompting",
    "debug": "topic/debugging",
    "architect": "topic/architecture",
    "refactor": "topic/refactoring",
    "test": "topic/testing",
    "deploy": "topic/deployment",
    "perform": "topic/performance",
    "typescript": "topic/typescript",
    "python": "topic/python",
    "react": "topic/react",
    "nextjs": "topic/nextjs",
    "next.js": "topic/nextjs",
    "sql": "topic/sql",
    "database": "topic/database",
    "prisma": "topic/database",
    "api": "topic/api",
    "auth": "topic/auth",
    "fantasy": "topic/fantasy-sports",
    "basketball": "topic/basketball",
    "obsidian": "topic/obsidian",
    "llm": "topic/ai-tools",
}


# --- Utility functions ---

def make_id(source: str, source_id: str, date: str, title: str) -> str:
    """Deterministic 12-char ID for deduplication, preferring source-native IDs."""
    raw = f"{source}:{source_id or ''}:{date}:{title}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def title_to_slug(title: str) -> str:
    """Convert a conversation title to a URL-safe slug, max 6 words."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    words = [w for w in slug.split("-") if w]
    return "-".join(words[:6])


def make_file_suffix(source_id: str, fallback_id: str) -> str:
    """Stable 8-char suffix for filenames, derived from source-native ID when available."""
    raw = source_id or fallback_id
    return hashlib.sha256(raw.encode()).hexdigest()[:8]


def first_substantive_exchange(exchanges: list[dict]) -> dict | None:
    for ex in exchanges:
        question = ex.get("question", "").strip()
        answer = ex.get("answer", "").strip()
        if question or answer:
            return ex
    return None


def build_signal_text(title: str, exchanges: list[dict]) -> str:
    """Text used for deterministic topic/entity heuristics in phase 1."""
    parts = [title]
    ex = first_substantive_exchange(exchanges)
    if ex:
        if ex.get("question", "").strip():
            parts.append(ex["question"].strip())
        if ex.get("answer", "").strip():
            parts.append(ex["answer"].strip())
    return "\n".join(parts)


def extract_tags(source: str, title: str, exchanges: list[dict]) -> list[str]:
    """Derive topic tags from the title plus the first substantive exchange."""
    base = [f"ai-history/{source}"]
    lower = build_signal_text(title, exchanges).lower()
    seen: set[str] = set()
    for keyword, tag in TOPIC_MAP.items():
        if keyword in lower and tag not in seen:
            base.append(tag)
            seen.add(tag)
    return base


def build_summary(title: str, exchanges: list[dict]) -> str:
    """Deterministic phase-1 summary using the title plus the first substantive exchange."""
    ex = first_substantive_exchange(exchanges)
    if not ex:
        return title or "No summary available."
    answer = re.sub(r"\s+", " ", ex.get("answer", "")).strip()
    question = re.sub(r"\s+", " ", ex.get("question", "")).strip()
    if answer:
        return f"{title}. {answer[:280]}".strip()
    if question:
        return f"{title}. {question[:220]}".strip()
    return title or "No summary available."


def score_quality(exchanges: list[dict]) -> str:
    """
    Return 'keep' or 'deferred'.
    Deferred if fewer than MIN_EXCHANGE_COUNT complete Q&A pairs,
    or if total assistant word count is below MIN_ASSISTANT_WORDS.
    """
    if len(exchanges) < MIN_EXCHANGE_COUNT:
        return "deferred"
    total_words = sum(len(ex.get("answer", "").split()) for ex in exchanges)
    if total_words < MIN_ASSISTANT_WORDS:
        return "deferred"
    return "keep"


def messages_to_exchanges(messages: list[dict]) -> list[dict]:
    """
    Convert an ordered list of {role, text, time} dicts into
    a list of {question, answer} exchange dicts.
    Consecutive assistant messages are joined; orphan assistant messages are skipped.
    """
    exchanges: list[dict] = []
    i = 0
    while i < len(messages):
        if messages[i]["role"] == "user":
            question = messages[i]["text"]
            answer_parts: list[str] = []
            i += 1
            while i < len(messages) and messages[i]["role"] == "assistant":
                text = messages[i]["text"].strip()
                if text:
                    answer_parts.append(text)
                i += 1
            answer = "\n\n".join(answer_parts)
            if question.strip():
                exchanges.append({"question": question, "answer": answer})
        else:
            i += 1
    return exchanges


def select_key_exchanges(exchanges: list[dict], n: int = 5) -> list[dict]:
    """
    Return up to n exchanges, selecting the most substantive (longest answers)
    while preserving original order.
    """
    if len(exchanges) <= n:
        return exchanges
    indexed = sorted(enumerate(exchanges), key=lambda x: len(x[1].get("answer", "")), reverse=True)
    top_indices = sorted(idx for idx, _ in indexed[:n])
    return [exchanges[i] for i in top_indices]


# --- ChatGPT parser ---

def parse_chatgpt_messages(mapping: dict) -> list[dict]:
    """
    Extract user and assistant messages from a ChatGPT mapping dict.
    Returns messages sorted by create_time ascending.
    """
    messages: list[dict] = []
    for node in mapping.values():
        msg = node.get("message")
        if not msg:
            continue
        role = msg.get("author", {}).get("role", "")
        if role not in ("user", "assistant"):
            continue
        parts = msg.get("content", {}).get("parts", [])
        text = " ".join(str(p) for p in parts if isinstance(p, str)).strip()
        if not text or text == "...":
            continue
        create_time = msg.get("create_time") or 0.0
        messages.append({"role": role, "text": text, "time": float(create_time)})
    messages.sort(key=lambda x: x["time"])
    return messages


def parse_chatgpt_conversation(raw: dict, batch_id: str) -> dict:
    """Parse a single ChatGPT conversation object into a normalized conv dict."""
    title = (raw.get("title") or "Untitled Conversation").strip()
    create_time = float(raw.get("create_time") or 0)
    date = datetime.fromtimestamp(create_time, tz=timezone.utc).strftime("%Y-%m-%d")
    source_id = str(raw.get("conversation_id") or raw.get("id") or "")
    mapping = raw.get("mapping") or {}
    messages = parse_chatgpt_messages(mapping)
    exchanges = messages_to_exchanges(messages)
    key_exchanges = select_key_exchanges(exchanges)
    quality = score_quality(exchanges)
    slug = title_to_slug(title)
    tags = extract_tags("chatgpt", title, exchanges)
    topic_tags = [t for t in tags if t.startswith("topic/")]
    summary = build_summary(title, exchanges)
    return {
        "id": make_id("chatgpt", source_id, date, title),
        "source": "chatgpt",
        "source_id": source_id,
        "model": "unknown",
        "date": date,
        "title": title,
        "slug": slug,
        "tags": tags,
        "topic_tags": topic_tags,
        "batch_id": batch_id,
        "quality": quality,
        "summary": summary or "No summary available.",
        "key_exchanges": key_exchanges,
        "exchange_count": len(exchanges),
    }


# --- Claude parser ---

def iso_to_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def iso_to_ts(value: str, fallback: float = 0.0) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return fallback


def extract_claude_message_text(message: dict) -> str:
    """
    Prefer the top-level text field when present. Fall back to concatenating
    `content[]` items of type `text`. Ignore `thinking`, `tool_use`,
    `tool_result`, and `token_budget` in phase 1 exchange extraction.
    """
    text = re.sub(r"\s+", " ", (message.get("text") or "")).strip()
    if text:
        return text
    parts: list[str] = []
    for part in message.get("content") or []:
        if not isinstance(part, dict):
            continue
        if part.get("type") != "text":
            continue
        chunk = re.sub(r"\s+", " ", (part.get("text") or "")).strip()
        if chunk:
            parts.append(chunk)
    return "\n\n".join(parts).strip()


def parse_claude_conversation(raw: dict, batch_id: str) -> dict:
    """Parse a single Claude conversation object into a normalized conv dict."""
    title = (raw.get("name") or "Untitled Conversation").strip()
    source_id = str(raw.get("uuid") or "")
    created_at = raw.get("created_at") or ""
    date = iso_to_date(created_at)
    messages_raw = raw.get("chat_messages") or []
    messages: list[dict] = []
    for m in messages_raw:
        sender = (m.get("sender") or "").strip().lower()
        if sender in ("human", "user"):
            role = "user"
        elif sender == "assistant":
            role = "assistant"
        else:
            continue
        text = extract_claude_message_text(m)
        if text:
            messages.append({
                "role": role,
                "text": text,
                "time": iso_to_ts(m.get("created_at") or created_at),
            })
    messages.sort(key=lambda x: x["time"])
    exchanges = messages_to_exchanges(messages)
    key_exchanges = select_key_exchanges(exchanges)
    quality = score_quality(exchanges)
    slug = title_to_slug(title)
    tags = extract_tags("claude", title, exchanges)
    topic_tags = [t for t in tags if t.startswith("topic/")]
    summary = build_summary(title, exchanges)
    return {
        "id": make_id("claude", source_id, date, title),
        "source": "claude",
        "source_id": source_id,
        "model": "unknown",
        "date": date,
        "title": title,
        "slug": slug,
        "tags": tags,
        "topic_tags": topic_tags,
        "batch_id": batch_id,
        "quality": quality,
        "summary": summary or "No summary available.",
        "key_exchanges": key_exchanges,
        "exchange_count": len(exchanges),
    }


# --- Markdown renderer ---

def render_markdown(conv: dict) -> str:
    """Render a normalized conv dict as an Obsidian markdown note."""
    tags_yaml = "\n".join(f"  - {t}" for t in conv["tags"])
    exchanges_md = ""
    for ex in conv["key_exchanges"]:
        q = ex["question"].replace("\n", " ").strip()
        a = ex["answer"].strip()
        exchanges_md += f"\n**Q:** {q}\n\n**A:** {a}\n"
    if not exchanges_md:
        exchanges_md = "\n<!-- No exchanges extracted -->\n"
    return (
        f"---\n"
        f"type: ai-history\n"
        f"source: {conv['source']}\n"
        f"model: {conv.get('model', 'unknown')}\n"
        f"date: {conv['date']}\n"
        f"title: \"{conv['title']}\"\n"
        f"slug: {conv['slug']}\n"
        f"tags:\n{tags_yaml}\n"
        f"import_batch: {conv['batch_id']}\n"
        f"quality: {conv['quality']}\n"
        f"---\n\n"
        f"## Summary\n\n{conv['summary']}\n\n"
        f"## Why This Mattered\n\n"
        f"<!-- Fill in: why past-you was asking this, what problem it connected to, "
        f"why future-you might care -->\n\n"
        f"## Key Exchanges\n{exchanges_md}\n"
        f"## Concepts Discussed\n\n"
        f"<!-- Add [[wikilinks]] to concept pages if applicable -->\n\n"
        f"## Notes\n\n"
        f"<!-- Manual additions post-import -->\n"
    )
```

- [ ] **Step 2: Run the tests**

```bash
cd ~/AIOS && python3 -m pytest tests/test_import_ai_history.py -v
```

Expected: all tests pass. Fix any failures before continuing.

- [ ] **Step 3: Commit**

```bash
cd ~/AIOS
git init 2>/dev/null || true
git add bin/import_ai_history.py tests/test_import_ai_history.py tests/fixtures/
git commit -m "feat: add AI history import core module with tests"
```

---

### Task 6: Import CLI with Dry-Run Mode [Completed 2026-04-02]

**Outcome:** Implemented in `~/AIOS/bin/import-ai-history.py`. The shipped CLI supports `chatgpt|claude|codex`, accepts file or directory-style exports where applicable, supports `--dry-run`, stages markdown into `~/AIOS/staging/ai-history/ready/`, writes SQLite rows, and skips duplicates by `id`.

**Files:**
- Create: `~/AIOS/bin/import-ai-history.py`

This CLI wraps the core module, handles file I/O, writes to staging, and writes batch metadata to SQLite.

- [ ] **Step 1: Write the CLI**

Write `~/AIOS/bin/import-ai-history.py`:

```python
#!/usr/bin/env python3
"""
AIOS: import-ai-history — CLI entry point

Usage:
  import-ai-history.py --source chatgpt --file raw/conversations.json
  import-ai-history.py --source chatgpt --file raw/conversations.json --dry-run
  import-ai-history.py --source claude  --file raw/claude-export/conversations.json
  import-ai-history.py --source claude  --file raw/claude-export/conversations.json --batch 20260401104530--claude
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow import from same directory
sys.path.insert(0, str(Path(__file__).parent))
from import_ai_history import (
    make_file_suffix,
    parse_chatgpt_conversation,
    parse_claude_conversation,
    render_markdown,
)

DB = Path.home() / "AIOS/data/aios.db"
READY_DIR = Path.home() / "AIOS/staging/ai-history/ready"


def make_batch_id(source: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{timestamp}--{source}"


def load_export(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array at top level, got {type(data).__name__}")
    return data


def get_existing_ids(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute("SELECT id FROM ai_history_imports")
    return {row[0] for row in cur.fetchall()}


def source_dir_name(source: str) -> str:
    names = {"chatgpt": "ChatGPT", "claude": "Claude", "codex": "Codex"}
    return names[source]


def stage_conversation(conv: dict, dry_run: bool) -> Path | None:
    """Write conversation markdown to staging area. Returns path written."""
    source_cap = source_dir_name(conv["source"])
    year = conv["date"][:4]
    dest_dir = READY_DIR / source_cap / year
    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
    file_suffix = make_file_suffix(conv.get("source_id", ""), conv["id"])
    filename = f"{conv['date']}-{conv['slug']}--{file_suffix}.md"
    dest = dest_dir / filename
    if not dry_run:
        dest.write_text(render_markdown(conv))
    return dest


def write_to_db(conn: sqlite3.Connection, conv: dict, staged_path: Path) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO ai_history_imports
          (id, batch_id, source, source_id, model, conversation_date, title, slug, topic_tags, quality, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'staged')
        """,
        (conv["id"], conv["batch_id"], conv["source"], conv.get("source_id", ""),
         conv.get("model", "unknown"), conv["date"], conv["title"], conv["slug"],
         json.dumps(conv.get("topic_tags", [])), conv["quality"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import AI conversation history")
    parser.add_argument("--source", required=True, choices=["chatgpt", "claude"])
    parser.add_argument("--file",   required=True, help="Path to export file (ChatGPT/Claude JSON now; Codex JSONL/directory in Task 11)")
    parser.add_argument("--batch",  default=None,  help="Batch ID (default: auto YYYYMMDDHHMMSS--source)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be imported without writing files or DB")
    args = parser.parse_args()

    batch_id = args.batch or make_batch_id(args.source)
    export_path = Path(args.file).expanduser()
    if not export_path.exists():
        print(f"ERROR: file not found: {export_path}", file=sys.stderr)
        sys.exit(1)

    raw_conversations = load_export(str(export_path))
    parse_fn = parse_chatgpt_conversation if args.source == "chatgpt" else parse_claude_conversation

    conn = sqlite3.connect(str(DB))
    existing_ids = get_existing_ids(conn)

    total = 0
    keep_count = 0
    deferred_count = 0
    duplicate_count = 0
    errors = 0

    for raw in raw_conversations:
        try:
            conv = parse_fn(raw, batch_id)
        except Exception as e:
            errors += 1
            if args.dry_run:
                print(f"  PARSE ERROR: {e}")
            continue

        if conv["id"] in existing_ids:
            duplicate_count += 1
            continue

        total += 1
        if conv["quality"] == "keep":
            keep_count += 1
        else:
            deferred_count += 1

        if args.dry_run:
            flag = "" if conv["quality"] == "keep" else "  [deferred]"
            print(f"  {conv['date']}  {conv['title'][:60]:<60}  {conv['exchange_count']} exchanges{flag}")
        else:
            staged_path = stage_conversation(conv, dry_run=False)
            write_to_db(conn, conv, staged_path)

    if conn and not args.dry_run:
        conn.commit()
    if conn:
        conn.close()

    print(f"\n{'DRY RUN — ' if args.dry_run else ''}Batch {batch_id}")
    print(f"  Source:     {args.source}")
    print(f"  Total:      {total}")
    print(f"  Keep:       {keep_count}")
    print(f"  Deferred:   {deferred_count}")
    print(f"  Duplicates: {duplicate_count}")
    print(f"  Errors:     {errors}")
    if not args.dry_run:
        print(f"  Staged to:  {READY_DIR}")
        print(f"\nNext: review-imports.sh --batch {batch_id}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make the CLI executable**

```bash
chmod +x ~/AIOS/bin/import-ai-history.py
```

- [ ] **Step 3: Dry-run against the fixture**

```bash
python3 ~/AIOS/bin/import-ai-history.py \
  --source chatgpt \
  --file ~/AIOS/tests/fixtures/chatgpt_sample.json \
  --dry-run
```

Expected output (similar to):
```
  2024-03-15  Context Windows and Retrieval                            2 exchanges
  2024-03-15  Hi                                                       1 exchanges  [deferred]

DRY RUN — Batch 20260401104530--chatgpt
  Source:     chatgpt
  Total:      2
  Keep:       1
  Deferred:   1
  Duplicates: 0
  Errors:     0
```

- [ ] **Step 4: Commit**

```bash
cd ~/AIOS
git add bin/import-ai-history.py
git commit -m "feat: add import-ai-history CLI with dry-run mode"
```

---

### Task 7: First Real Import Run [Blocked — ChatGPT export not available as of 2026-04-02]

**Status note:** The real ChatGPT import has not been run yet because no export file is available. The parser and CLI are ready; complete this task once a ChatGPT export is staged under `~/AIOS/staging/ai-history/raw/`.

**Files:**
- No new files — validates pipeline against actual export data

- [ ] **Step 1: Copy your ChatGPT export to staging**

```bash
# ChatGPT export is typically named conversations.json inside a zip
# Extract it if needed, then:
cp /path/to/conversations.json ~/AIOS/staging/ai-history/raw/chatgpt-export-$(date +%Y%m%d).json
```

- [ ] **Step 2: Inspect the raw format**

```bash
python3 -c "
import json
with open('$(ls ~/AIOS/staging/ai-history/raw/*.json | head -1)') as f:
    data = json.load(f)
first = data[0]
print('Top-level keys:', list(first.keys()))
print('Title:', first.get('title'))
print('create_time:', first.get('create_time'))
mapping = first.get('mapping', {})
first_node = next(iter(mapping.values()), {})
print('Mapping node keys:', list(first_node.keys()))
msg = first_node.get('message', {})
print('Message keys:', list(msg.keys()) if msg else 'None')
"
```

If the format differs from the fixture — for example if `content.parts` contains dicts instead of strings — note it and adjust `parse_chatgpt_messages` before proceeding.

- [ ] **Step 3: Dry-run against your real export**

```bash
EXPORT=$(ls ~/AIOS/staging/ai-history/raw/chatgpt-export-*.json | head -1)
python3 ~/AIOS/bin/import-ai-history.py \
  --source chatgpt \
  --file "$EXPORT" \
  --dry-run 2>&1 | tail -20
```

Review the statistics. Check that deferred count is reasonable and that obviously substantive conversations are not being downgraded because of weak titles.

- [ ] **Step 4: Run the actual import**

```bash
EXPORT=$(ls ~/AIOS/staging/ai-history/raw/chatgpt-export-*.json | head -1)
python3 ~/AIOS/bin/import-ai-history.py \
  --source chatgpt \
  --file "$EXPORT"
```

- [ ] **Step 5: Spot-check 3 staged notes**

```bash
ls ~/AIOS/staging/ai-history/ready/ChatGPT/ | head -5
# Pick one and inspect it:
cat "$(ls ~/AIOS/staging/ai-history/ready/ChatGPT/**/*.md | head -1)"
```

Verify:
- `type: ai-history` is in the frontmatter
- No `status:`, `project:`, or `priority:` fields
- `## Why This Mattered` section is present (with placeholder comment)
- `## Key Exchanges` has actual content

- [ ] **Step 6: Verify SQLite records**

```bash
sqlite3 ~/AIOS/data/aios.db "
SELECT source, quality, status, COUNT(*) as n
FROM ai_history_imports
GROUP BY source, quality, status;
"
```

---

### Task 8: `review-imports.sh` [Completed 2026-04-02]

**Outcome:** Implemented in `~/AIOS/bin/review-imports.sh`. The current script supports `--batch` and `--all-staged`, lists keep/deferred notes, and now includes deferred notes in aggregate topic analysis so thin conversations still contribute to batch-level pattern detection.

**Files:**
- Create: `~/AIOS/bin/review-imports.sh`

- [ ] **Step 1: Write the script**

Write `~/AIOS/bin/review-imports.sh`:

```bash
#!/usr/bin/env bash
# AIOS: review-imports.sh — read-only batch review
# Usage:
#   review-imports.sh --batch 20260401104530--chatgpt
#   review-imports.sh --all-staged
set -euo pipefail

DB=~/AIOS/data/aios.db
SEP="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ $# -eq 0 ]]; then
  echo "Usage: review-imports.sh --batch <id>"
  echo "       review-imports.sh --all-staged"
  exit 1
fi

MODE="$1"
BATCH_ID="${2:-}"

if [[ "$MODE" == "--all-staged" ]]; then
  echo ""
  echo "All staged batches"
  echo "$SEP"
  sqlite3 "$DB" "
    SELECT batch_id,
           source,
           COUNT(*) as total,
           SUM(CASE WHEN quality='deferred' THEN 1 ELSE 0 END) as deferred,
           MIN(conversation_date) || ' → ' || MAX(conversation_date) as date_range
    FROM ai_history_imports
    WHERE status = 'staged'
    GROUP BY batch_id, source
    ORDER BY batch_id DESC;
  " | while IFS='|' read -r bid src total deferred range; do
    echo "  Batch $bid ($src): $total conversations, $deferred deferred — $range"
  done
  echo ""
  exit 0
fi

if [[ "$MODE" == "--batch" && -n "$BATCH_ID" ]]; then
  echo ""
  echo "Batch: $BATCH_ID"
  echo "$SEP"

  # Summary stats
  sqlite3 "$DB" "
    SELECT
      source,
      COUNT(*) as total,
      SUM(CASE WHEN quality='keep'     THEN 1 ELSE 0 END) as keep_count,
      SUM(CASE WHEN quality='deferred' THEN 1 ELSE 0 END) as deferred_count,
      MIN(conversation_date) as earliest,
      MAX(conversation_date) as latest
    FROM ai_history_imports
    WHERE batch_id = '$BATCH_ID'
    GROUP BY source
    ORDER BY source;
  " | while IFS='|' read -r src total keep deferred earliest latest; do
    echo "  Source:   $src"
    echo "  Total:    $total"
    echo "  Keep:     $keep"
    echo "  Deferred: $deferred"
    echo "  Range:    $earliest → $latest"
  done

  echo ""
  echo "Deferred conversations (not promoted by default):"
  sqlite3 "$DB" "
    SELECT id, conversation_date, title
    FROM ai_history_imports
    WHERE batch_id = '$BATCH_ID' AND quality = 'deferred'
    ORDER BY conversation_date;
  " | while IFS='|' read -r id date title; do
    echo "  $id [$date] ${title:0:60}"
  done

  echo ""
  echo "Keep conversations (use IDs with --exclude):"
  sqlite3 "$DB" "
    SELECT id, conversation_date, title
    FROM ai_history_imports
    WHERE batch_id = '$BATCH_ID' AND quality = 'keep'
    ORDER BY conversation_date
    LIMIT 20;
  " | while IFS='|' read -r id date title; do
    echo "  $id [$date] ${title:0:60}"
  done

  echo ""
  echo "Entity candidates (topic tags in 3+ conversations this batch):"
  python3 - <<'PY' "$DB" "$BATCH_ID"
import json
import sqlite3
import sys

db, batch_id = sys.argv[1], sys.argv[2]
conn = sqlite3.connect(db)
rows = conn.execute(
    "SELECT topic_tags FROM ai_history_imports WHERE batch_id = ? AND quality = 'keep'",
    (batch_id,),
).fetchall()

counts = {}
for (payload,) in rows:
    for tag in json.loads(payload or "[]"):
        counts[tag] = counts.get(tag, 0) + 1

matches = sorted(((tag, n) for tag, n in counts.items() if n >= 3), key=lambda item: (-item[1], item[0]))[:15]
if not matches:
    print("  (none above threshold)")
else:
    for tag, n in matches:
        print(f"  {tag} ({n} conversations)")
PY

  echo ""
  echo "$SEP"
  echo "To promote:  promote-imports.sh --batch $BATCH_ID"
  echo "To exclude:  promote-imports.sh --batch $BATCH_ID --exclude id1,id2"
  echo ""
  exit 0
fi

echo "Unknown mode: $MODE"
exit 1
```

- [ ] **Step 2: Make executable**

```bash
chmod +x ~/AIOS/bin/review-imports.sh
```

- [ ] **Step 3: Run against your staged batch**

```bash
# Get the batch ID from step 7:
BATCH=$(sqlite3 ~/AIOS/data/aios.db "SELECT DISTINCT batch_id FROM ai_history_imports ORDER BY created_at DESC LIMIT 1;")
~/AIOS/bin/review-imports.sh --batch "$BATCH"
```

Review the output. Check that the deferred list looks right, the keep list exposes usable IDs for `--exclude`, and entity candidates are plausible.

- [ ] **Step 4: Commit**

```bash
cd ~/AIOS
git add bin/review-imports.sh
git commit -m "feat: add review-imports.sh for staged batch inspection"
```

---

### Task 9: `promote-imports.sh` [Completed 2026-04-02]

**Outcome:** Implemented in `~/AIOS/bin/promote-imports.sh`. The current script promotes `quality='keep'` rows by default, leaves deferred rows staged, supports `--exclude`, and now supports `--include-deferred` when aggregate thin-chat signal should be preserved in the archive.

**Files:**
- Create: `~/AIOS/bin/promote-imports.sh`

- [ ] **Step 1: Write the script**

Write `~/AIOS/bin/promote-imports.sh`:

```bash
#!/usr/bin/env bash
# AIOS: promote-imports.sh — move staged notes to vault and scaffold batch synthesis
# Usage:
#   promote-imports.sh --batch 20260401104530--chatgpt
#   promote-imports.sh --batch 20260401104530--chatgpt --exclude id1,id2
set -euo pipefail

DB=~/AIOS/data/aios.db
READY=~/AIOS/staging/ai-history/ready
VAULT=~/Vaults/Command-Center/"09 Archive/AI History"
NOW=$(date "+%Y-%m-%d %H:%M")

source_dir_name() {
  case "$1" in
    chatgpt) echo "ChatGPT" ;;
    claude) echo "Claude" ;;
    codex) echo "Codex" ;;
    *) echo "$1" ;;
  esac
}

make_file_suffix() {
  python3 -c "import hashlib, sys; raw = sys.argv[1] or sys.argv[2]; print(hashlib.sha256(raw.encode()).hexdigest()[:8])" "$1" "$2"
}

if [[ $# -eq 0 || "$1" != "--batch" ]]; then
  echo "Usage: promote-imports.sh --batch <id> [--exclude id1,id2]"
  exit 1
fi

BATCH_ID="$2"
EXCLUDE_IDS=""
if [[ "${3:-}" == "--exclude" ]]; then
  EXCLUDE_IDS="${4:-}"
fi

# Build exclusion list
IFS=',' read -ra EXCLUDED <<< "$EXCLUDE_IDS"
declare -A EXCLUDED_MAP
for item in "${EXCLUDED[@]}"; do
  EXCLUDED_MAP["$item"]=1
done

echo ""
echo "Promoting batch: $BATCH_ID"
echo "Excluded ids:    ${EXCLUDE_IDS:-none}"
echo ""

# Get staged conversations for this batch
promoted=0
skipped=0
errors=0

while IFS='|' read -r id source source_id quality slug conversation_date; do
  # Skip if explicitly excluded
  if [[ -n "${EXCLUDED_MAP[$id]+_}" ]]; then
    echo "  EXCLUDED  $id"
    skipped=$((skipped + 1))
    continue
  fi

  # Skip deferred unless explicitly included (deferred stays staged)
  if [[ "$quality" == "deferred" ]]; then
    skipped=$((skipped + 1))
    continue
  fi

  # Find the staged file
  year="${conversation_date:0:4}"
  src_cap="$(source_dir_name "$source")"
  suffix="$(make_file_suffix "$source_id" "$id")"
  staged_file="$READY/$src_cap/$year/${conversation_date}-${slug}--${suffix}.md"

  if [[ ! -f "$staged_file" ]]; then
    echo "  MISSING   $id (staged file not found)"
    errors=$((errors + 1))
    continue
  fi

  # Create destination directory
  dest_dir="$VAULT/$src_cap/$year"
  mkdir -p "$dest_dir"
  dest="$dest_dir/${conversation_date}-${slug}--${suffix}.md"

  cp "$staged_file" "$dest"

  # Update SQLite
  sqlite3 "$DB" "
    UPDATE ai_history_imports
    SET status = 'promoted',
        vault_path = '$dest',
        promoted_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE id = '$id';
  "

  echo "  PROMOTED  $dest"
  promoted=$((promoted + 1))

done < <(sqlite3 "$DB" "
  SELECT id, source, source_id, quality, slug, conversation_date
  FROM ai_history_imports
  WHERE batch_id = '$BATCH_ID' AND status = 'staged'
  ORDER BY conversation_date;
")

# Stats for batch synthesis scaffold
total_count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM ai_history_imports WHERE batch_id='$BATCH_ID';")
total_promoted=$(sqlite3 "$DB" "SELECT COUNT(*) FROM ai_history_imports WHERE batch_id='$BATCH_ID' AND status='promoted';")
total_deferred=$(sqlite3 "$DB" "SELECT COUNT(*) FROM ai_history_imports WHERE batch_id='$BATCH_ID' AND quality='deferred';")
date_range=$(sqlite3 "$DB" "SELECT MIN(conversation_date)||' → '||MAX(conversation_date) FROM ai_history_imports WHERE batch_id='$BATCH_ID';")
source_val=$(sqlite3 "$DB" "
  SELECT CASE
    WHEN COUNT(DISTINCT source) = 1 THEN MIN(source)
    ELSE 'mixed'
  END
  FROM ai_history_imports
  WHERE batch_id='$BATCH_ID';
")

# Scaffold batch synthesis note
batch_note="$VAULT/_Batch-${BATCH_ID}.md"
cat > "$batch_note" << EOF
---
type: archive-batch
batch_id: ${BATCH_ID}
source: ${source_val}
date_range: "${date_range}"
conversation_count: ${total_count}
promoted_count: ${total_promoted}
deferred_count: ${total_deferred}
promoted_at: ${NOW}
---

# Batch ${BATCH_ID} — What This Archive Taught Me

<!-- Fill in after reviewing promoted conversations. This is where historic data becomes a brain. -->

## Recurring Themes

-

## Repeated Blind Spots

-

## Prompts That Kept Reappearing

-

## Problems Solved Multiple Times

-

## Concepts That Probably Deserve a Page

<!-- Check entity candidates from review-imports.sh output -->
- [ ]

EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Batch $BATCH_ID complete"
echo "  Promoted: $promoted"
echo "  Skipped:  $skipped (deferred or excluded)"
echo "  Errors:   $errors"
echo ""
echo "Batch synthesis note scaffolded: $batch_note"
echo ""
echo "Next steps:"
echo "  1. Open $batch_note and fill in the 'What This Archive Taught Me' sections"
echo "  2. Add a link to this batch in 09 Archive/AI History/_Index.md"
echo "  3. Create concept pages in 06 Knowledge/Concepts/ for any topics above threshold"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x ~/AIOS/bin/promote-imports.sh
```

- [ ] **Step 3: Run promote on your batch (test with one excluded ID first)**

```bash
BATCH=$(sqlite3 ~/AIOS/data/aios.db "SELECT DISTINCT batch_id FROM ai_history_imports ORDER BY created_at DESC LIMIT 1;")

# Preview what would happen: check the review output first
~/AIOS/bin/review-imports.sh --batch "$BATCH"

# Then promote
~/AIOS/bin/promote-imports.sh --batch "$BATCH"
```

- [ ] **Step 4: Verify promotion**

```bash
# Notes should be in vault
find ~/Vaults/Command-Center/"09 Archive/AI History" -name "*.md" | head -10

# SQLite should reflect promoted status
sqlite3 ~/AIOS/data/aios.db "
SELECT status, COUNT(*) FROM ai_history_imports GROUP BY status;
"

# Obsidian search: open vault, search for type:ai-history — should find notes
# Confirm Open Actions dashboard still shows zero results from archive
```

- [ ] **Step 5: Fill in `_Index.md` coverage row**

Manually update `09 Archive/AI History/_Index.md` to add a row to the coverage table and a link to `_Batch-{id}`.

- [ ] **Step 6: Commit**

```bash
cd ~/AIOS
git add bin/promote-imports.sh
git commit -m "feat: add promote-imports.sh with batch synthesis note scaffold"
```

---

### Task 10: Claude Export Format Support [Completed 2026-04-02]

**Outcome:** Verified against the real Claude bundle staged at `~/AIOS/staging/ai-history/raw/claude-export-20260401/`. Batch `20260402033854--claude` imported 145 conversations, promoted 59, and left 86 deferred. A later rerun confirmed deduplication with `Duplicates: 145`.

**Files:**
- Modify: `~/AIOS/bin/import_ai_history.py` (already written — Claude parser exists)
- Modify: `~/AIOS/tests/test_import_ai_history.py` (add Claude-specific tests)

- [ ] **Step 1: Inspect the actual Claude export bundle**

```bash
# Claude exports may arrive as a bundle directory containing conversations.json
cp -R /path/to/claude-export-bundle ~/AIOS/staging/ai-history/raw/claude-export-$(date +%Y%m%d)

python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

bundle = sorted(Path.home().glob("AIOS/staging/ai-history/raw/claude-export-*"))[0]
path = bundle / "conversations.json" if bundle.is_dir() else bundle
with open(path) as f:
    data = json.load(f)

first = data[0]
print("Top-level keys:", list(first.keys()))
msgs = first.get("chat_messages", [])
if msgs:
    print("Message keys:", list(msgs[0].keys()))
    print("Sender values:", sorted({(m.get("sender") or "").lower() for m in msgs[:50]}))
    content_types = Counter(
        part.get("type")
        for m in msgs[:50]
        for part in (m.get("content") or [])
        if isinstance(part, dict)
    )
    print("Content types:", dict(content_types))
PY
```

On 2026-04-01, the inspected Claude export used:
- top-level keys: `uuid`, `name`, `summary`, `created_at`, `updated_at`, `account`, `chat_messages`
- message keys: `uuid`, `text`, `content`, `sender`, `created_at`, `updated_at`, `attachments`, `files`
- sender values: `human`, `assistant`
- content types: `text`, `thinking`, `tool_use`, `tool_result`, `token_budget`

Treat this shape as the ground truth. Do not assume the export is text-only just because many messages also have a top-level `text` field.

- [ ] **Step 2: Add Claude tests for the real export shape**

Append to `~/AIOS/tests/test_import_ai_history.py`:

```python
def test_claude_parse_uses_content_text_when_text_field_is_blank():
    from import_ai_history import parse_claude_conversation
    raw = {
        "uuid": "test",
        "name": "Test Conversation",
        "created_at": "2025-01-10T10:00:00+00:00",
        "chat_messages": [
            {
                "uuid": "m1",
                "text": "How does X work?",
                "content": [{"type": "text", "text": "How does X work?"}],
                "sender": "human",
                "created_at": "2025-01-10T10:00:00+00:00",
            },
            {
                "uuid": "m2",
                "text": "",
                "content": [
                    {"type": "thinking", "thinking": "Comparing options"},
                    {"type": "text", "text": "X works by " + "word " * 60},
                    {"type": "tool_use", "name": "web_search", "input": {"query": "x"}},
                    {"type": "tool_result", "name": "web_search", "content": []},
                ],
                "sender": "assistant",
                "created_at": "2025-01-10T10:01:00+00:00",
            },
            {
                "uuid": "m3",
                "text": "What about Y?",
                "content": [{"type": "text", "text": "What about Y?"}],
                "sender": "human",
                "created_at": "2025-01-10T10:02:00+00:00",
            },
            {
                "uuid": "m4",
                "text": "Y is different " + "word " * 60,
                "content": [{"type": "text", "text": "Y is different " + "word " * 60}],
                "sender": "assistant",
                "created_at": "2025-01-10T10:03:00+00:00",
            },
        ],
    }
    conv = parse_claude_conversation(raw, "test-batch")
    assert conv["quality"] == "keep"
    assert "X works by" in conv["summary"]


def test_claude_parse_handles_capitalized_sender():
    from import_ai_history import parse_claude_conversation
    raw = {
        "uuid": "test",
        "name": "Sender Variant",
        "created_at": "2025-01-10T10:00:00+00:00",
        "chat_messages": [
            {"uuid": "m1", "text": "Q1", "content": [{"type": "text", "text": "Q1"}], "sender": "User", "created_at": "2025-01-10T10:00:00+00:00"},
            {"uuid": "m2", "text": "A1 " + "word " * 60, "content": [{"type": "text", "text": "A1 " + "word " * 60}], "sender": "Assistant", "created_at": "2025-01-10T10:01:00+00:00"},
            {"uuid": "m3", "text": "Q2", "content": [{"type": "text", "text": "Q2"}], "sender": "User", "created_at": "2025-01-10T10:02:00+00:00"},
            {"uuid": "m4", "text": "A2 " + "word " * 60, "content": [{"type": "text", "text": "A2 " + "word " * 60}], "sender": "Assistant", "created_at": "2025-01-10T10:03:00+00:00"},
        ],
    }
    conv = parse_claude_conversation(raw, "test-batch")
    assert conv["quality"] == "keep"
```

- [ ] **Step 3: Update `parse_claude_conversation` to match the real export**

Use the implementation from Task 5:
- normalize sender with `.strip().lower()` and map `human|user -> user`, `assistant -> assistant`
- sort messages by `created_at`
- prefer the top-level `text` field, but fall back to `content[]` items of type `text`
- ignore `thinking`, `tool_use`, `tool_result`, and `token_budget` for phase-1 exchange extraction
- do not claim attachments or files are impossible just because phase 1 ignores them in summaries

- [ ] **Step 4: Run full test suite**

```bash
cd ~/AIOS && python3 -m pytest tests/test_import_ai_history.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Dry-run Claude export**

```bash
EXPORT="$(ls -d ~/AIOS/staging/ai-history/raw/claude-export-* | head -1)/conversations.json"
python3 ~/AIOS/bin/import-ai-history.py \
  --source claude \
  --file "$EXPORT" \
  --dry-run 2>&1 | tail -20
```

- [ ] **Step 6: Full Claude import + promote**

```bash
EXPORT="$(ls -d ~/AIOS/staging/ai-history/raw/claude-export-* | head -1)/conversations.json"
python3 ~/AIOS/bin/import-ai-history.py \
  --source claude \
  --file "$EXPORT"

BATCH=$(sqlite3 ~/AIOS/data/aios.db "
  SELECT DISTINCT batch_id FROM ai_history_imports
  WHERE source='claude' ORDER BY created_at DESC LIMIT 1;
")
~/AIOS/bin/review-imports.sh --batch "$BATCH"
~/AIOS/bin/promote-imports.sh --batch "$BATCH"
```

- [ ] **Step 7: Commit**

```bash
cd ~/AIOS
git add bin/import_ai_history.py tests/test_import_ai_history.py
git commit -m "feat: verified Claude export format support"
```

---

### Task 11: Codex Local Session Format Support [Completed 2026-04-02]

**Outcome:** Implemented against a staged snapshot at `~/AIOS/staging/ai-history/raw/codex-export-20260401/`. Batch `20260402034120--codex` imported 314 sessions, promoted 57, and left 257 deferred. Fixture coverage and CLI support are now in place for the normalized Codex session shape.

**Files:**
- Create: `~/AIOS/tests/fixtures/codex_sample.json`
- Modify: `~/AIOS/bin/import_ai_history.py`
- Modify: `~/AIOS/bin/import-ai-history.py`
- Modify: `~/AIOS/tests/test_import_ai_history.py`

- [ ] **Step 1: Inspect the actual local Codex session store**

```bash
sqlite3 ~/.codex/state_5.sqlite "
  SELECT id, title, rollout_path
  FROM threads
  ORDER BY updated_at DESC
  LIMIT 5;
"

python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

path = sorted(Path.home().glob(".codex/sessions/**/*.jsonl"))[-1]
print("Inspecting:", path)

types = Counter()
roles = Counter()
phases = Counter()
with open(path) as f:
    for line in f:
        obj = json.loads(line)
        types[obj.get("type")] += 1
        if obj.get("type") == "response_item":
            payload = obj.get("payload") or {}
            if payload.get("type") == "message":
                roles[payload.get("role")] += 1
                phases[payload.get("phase") or "none"] += 1

print("event types:", dict(types))
print("message roles:", dict(roles))
print("assistant phases:", dict(phases))
PY
```

On 2026-04-01, the inspected Codex session store showed:
- raw source files under `~/.codex/sessions/**/*.jsonl` and `~/.codex/archived_sessions/*.jsonl`
- thread metadata in `~/.codex/session_index.jsonl` and `~/.codex/state_5.sqlite`
- rollout event types: `session_meta`, `event_msg`, `response_item`, `turn_context`, `compacted`
- message roles inside `response_item`: `developer`, `user`, `assistant`
- assistant phases: mostly `commentary`, plus `final_answer`

Treat the JSONL rollout files as the raw ground truth. Use:
- `session_meta.payload.id` as the stable Codex conversation ID
- `session_meta.payload.timestamp` as the conversation start date
- `session_index.jsonl` or `threads.title` as the preferred title source
- `response_item.payload.content[].text` from `role=user|assistant` as the text carrier

- [ ] **Step 2: Snapshot Codex raw data into staging**

```bash
SNAP=~/AIOS/staging/ai-history/raw/codex-export-$(date +%Y%m%d)
mkdir -p "$SNAP"
cp ~/.codex/session_index.jsonl "$SNAP/"
find ~/.codex/sessions -name '*.jsonl' -exec cp {} "$SNAP/" \;
find ~/.codex/archived_sessions -name '*.jsonl' -exec cp {} "$SNAP/" \;
```

This keeps the Codex raw source local and deterministic instead of relying on a separate product export feature.

- [ ] **Step 3: Create a representative normalized Codex fixture**

Write `~/AIOS/tests/fixtures/codex_sample.json` as a normalized session fixture derived from 1-2 real rollout files:

```json
[
  {
    "session_id": "019d4acf-e3a2-7f21-89b6-58add6d1e295",
    "title": "can read this plan ~/AIOS/docs/plans/2026-04-01-ai-history-import.md and then asses you confidence",
    "created_at": "2026-04-01T20:50:31.000Z",
    "source": "vscode",
    "model_provider": "openai",
    "rollout_path": "rollout-2026-04-01T16-50-31-019d4acf-e3a2-7f21-89b6-58add6d1e295.jsonl",
    "messages": [
      {
        "role": "user",
        "phase": "user",
        "text": "can read this plan ~/AIOS/docs/plans/2026-04-01-ai-history-import.md and then asses you confidence"
      },
      {
        "role": "assistant",
        "phase": "final_answer",
        "text": "I read ..."
      }
    ]
  }
]
```

Derive this fixture from actual `response_item` records. Exclude:
- `developer` messages
- `AGENTS.md` bootstrap text
- `<environment_context>` scaffolding
- assistant `phase == "commentary"` progress updates

- [ ] **Step 4: Add `load_codex_export()` and `parse_codex_conversation()`**

In `~/AIOS/bin/import_ai_history.py`, add a Codex loader and parser:

```python
def load_codex_export(path: str) -> list[dict]:
    """
    Accept either a single rollout .jsonl file or a directory of rollout files.
    Read session_index.jsonl when present to map session IDs to human titles.
    Normalize each rollout into:
      {
          "session_id": ...,
          "title": ...,
          "created_at": ...,
          "source": ...,
          "model_provider": ...,
          "rollout_path": ...,
          "messages": [{"role": ..., "phase": ..., "text": ...}, ...],
      }
    """


def parse_codex_conversation(raw: dict, batch_id: str) -> dict:
    """
    Convert a normalized Codex session dict into the common conv shape.
    Use raw["session_id"] as source_id, raw["created_at"] for date,
    and pair filtered user messages with assistant final_answer messages.
    """
```

Implementation rules:
- title priority: normalized `title` from `session_index.jsonl` / `threads.title`, else first substantive user message
- message extraction: keep only user messages and assistant `final_answer` messages
- text extraction: concatenate `content[]` items of type `input_text` / `output_text`
- ignore `event_msg`, `turn_context`, `compacted`, and `developer` records
- ignore Codex commentary updates for phase-1 summaries and key exchanges

- [ ] **Step 5: Update the CLI for Codex**

In `~/AIOS/bin/import-ai-history.py`:

```python
from import_ai_history import (
    load_codex_export,
    make_file_suffix,
    parse_chatgpt_conversation,
    parse_claude_conversation,
    parse_codex_conversation,
    render_markdown,
)

def load_export(path: str, source: str) -> list[dict]:
    if source == "codex":
        return load_codex_export(path)
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array at top level, got {type(data).__name__}")
    return data

parser.add_argument("--source", required=True, choices=["chatgpt", "claude", "codex"])

parse_fn_map = {
    "chatgpt": parse_chatgpt_conversation,
    "claude": parse_claude_conversation,
    "codex": parse_codex_conversation,
}
parse_fn = parse_fn_map[args.source]
raw_conversations = load_export(str(export_path), args.source)
```

- [ ] **Step 6: Add Codex tests**

Append to `~/AIOS/tests/test_import_ai_history.py`:

```python
@pytest.fixture
def codex_sample():
    with open(FIXTURES / "codex_sample.json") as f:
        return json.load(f)


def test_codex_parse_structure(codex_sample):
    from import_ai_history import parse_codex_conversation
    conv = parse_codex_conversation(codex_sample[0], "test-batch")
    assert conv["source"] == "codex"
    assert conv["batch_id"] == "test-batch"
    assert "ai-history/codex" in conv["tags"]
    assert len(conv["slug"]) > 0


def test_codex_parse_filters_setup_and_commentary():
    from import_ai_history import parse_codex_conversation
    raw = {
        "session_id": "codex-1",
        "title": "",
        "created_at": "2026-04-01T20:54:50.554Z",
        "source": "vscode",
        "model_provider": "openai",
        "messages": [
            {"role": "user", "phase": "user", "text": "# AGENTS.md instructions for /tmp/repo"},
            {"role": "user", "phase": "user", "text": "<environment_context>...</environment_context>"},
            {"role": "user", "phase": "user", "text": "Summarize the import plan"},
            {"role": "assistant", "phase": "commentary", "text": "I’m opening the file now."},
            {"role": "assistant", "phase": "final_answer", "text": "The plan is strong but needs filename disambiguation."},
        ],
    }
    conv = parse_codex_conversation(raw, "test-batch")
    assert conv["title"] == "Summarize the import plan"
    assert conv["key_exchanges"][0]["question"] == "Summarize the import plan"
    assert "opening the file now" not in conv["summary"].lower()
```

- [ ] **Step 7: Run full test suite**

```bash
cd ~/AIOS && python3 -m pytest tests/test_import_ai_history.py -v
```

- [ ] **Step 8: Dry-run and import Codex**

```bash
EXPORT=$(ls -d ~/AIOS/staging/ai-history/raw/codex-export-* | head -1)
python3 ~/AIOS/bin/import-ai-history.py \
  --source codex \
  --file "$EXPORT" \
  --dry-run 2>&1 | tail -20

python3 ~/AIOS/bin/import-ai-history.py \
  --source codex \
  --file "$EXPORT"

BATCH=$(sqlite3 ~/AIOS/data/aios.db "
  SELECT DISTINCT batch_id FROM ai_history_imports
  WHERE source='codex' ORDER BY created_at DESC LIMIT 1;
")
~/AIOS/bin/review-imports.sh --batch "$BATCH"
~/AIOS/bin/promote-imports.sh --batch "$BATCH"
```

- [ ] **Step 9: Commit**

```bash
cd ~/AIOS
git add bin/import_ai_history.py bin/import-ai-history.py tests/test_import_ai_history.py tests/fixtures/codex_sample.json
git commit -m "feat: add Codex local session import support"
```

---

### Task 12: Deduplication Check [Partially Complete 2026-04-02]

**Outcome:** Unit coverage for stable IDs and non-collision is complete, and live deduplication was verified by re-running the Claude batch (`Duplicates: 145`). The specific real ChatGPT rerun described below remains blocked until Task 7 has a real export to re-import.

**Files:**
- Modify: `~/AIOS/bin/import_ai_history.py` (no changes — deduplication already in CLI)
- Modify: `~/AIOS/tests/test_import_ai_history.py` (add dedup test)

The CLI already skips conversations whose `id` exists in `ai_history_imports`. This task verifies that deduplication works correctly when re-running an import.

- [ ] **Step 1: Add dedup unit test**

Append to `~/AIOS/tests/test_import_ai_history.py`:

```python
def test_make_id_collision_on_same_conversation():
    """Two parses of the same conversation produce the same ID."""
    from import_ai_history import parse_chatgpt_conversation
    import json
    from pathlib import Path
    with open(Path.home() / "AIOS/tests/fixtures/chatgpt_sample.json") as f:
        sample = json.load(f)
    conv1 = parse_chatgpt_conversation(sample[0], "batch-a")
    conv2 = parse_chatgpt_conversation(sample[0], "batch-b")
    assert conv1["id"] == conv2["id"], "Same conversation must produce same ID regardless of batch"


def test_make_id_uses_source_native_id_for_same_title_same_day():
    """Two different conversations with the same title/day should not collide."""
    from import_ai_history import parse_chatgpt_conversation
    raw1 = {
        "id": "conv-aaa",
        "conversation_id": "conv-aaa",
        "title": "Repeated Title",
        "create_time": 1710460800.0,
        "mapping": {},
    }
    raw2 = {
        "id": "conv-bbb",
        "conversation_id": "conv-bbb",
        "title": "Repeated Title",
        "create_time": 1710460800.0,
        "mapping": {},
    }
    conv1 = parse_chatgpt_conversation(raw1, "batch-a")
    conv2 = parse_chatgpt_conversation(raw2, "batch-a")
    assert conv1["id"] != conv2["id"]
```

- [ ] **Step 2: Run the test**

```bash
cd ~/AIOS && python3 -m pytest tests/test_import_ai_history.py -k make_id -v
```

Expected: both dedup-related tests PASS.

- [ ] **Step 3: Integration test — re-run the ChatGPT import**

```bash
python3 ~/AIOS/bin/import-ai-history.py \
  --source chatgpt \
  --file "$(ls ~/AIOS/staging/ai-history/raw/chatgpt-export-*.json | head -1)" \
  2>&1 | grep "Duplicates:"
```

Expected: `Duplicates: N` where N equals the number of conversations previously imported. Zero new conversations processed.

- [ ] **Step 4: Commit**

```bash
cd ~/AIOS
git add tests/test_import_ai_history.py
git commit -m "test: strengthen deduplication coverage"
```

---

### Task 13: Health Check Integration [Completed 2026-04-02]

**Outcome:** `~/ai-os/scripts/health_check.sh` now reports promoted, staged, and deferred AI history counts from `ai_history_imports`, and the health dashboard refresh is working with the new rows.

**Files:**
- Modify: `~/ai-os/scripts/health_check.sh`

- [ ] **Step 1: Read the current health_check.sh**

```bash
cat ~/ai-os/scripts/health_check.sh
```

- [ ] **Step 2: Add import stats queries**

In `health_check.sh`, after the existing `OPEN_BUGS` query block, add:

```bash
# AI History import stats
AI_IMPORTED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM ai_history_imports WHERE status='promoted';" 2>/dev/null || echo 0)
AI_STAGED=$(sqlite3 "$DB"   "SELECT COUNT(*) FROM ai_history_imports WHERE status='staged';"   2>/dev/null || echo 0)
AI_DEFERRED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM ai_history_imports WHERE quality='deferred';" 2>/dev/null || echo 0)
```

- [ ] **Step 3: Add rows to the report table**

In the `cat > "$REPORT"` heredoc, add three rows to the `## At a Glance` table after the existing rows:

```bash
| AI history imported | ${AI_IMPORTED} |
| AI history staged (pending review) | ${AI_STAGED} |
| AI history deferred | ${AI_DEFERRED} |
```

The full table should read:

```markdown
| Metric | Value |
|--------|-------|
| Active projects | ${ACTIVE_PROJECTS} |
| Sessions (7 days) | ${SESSIONS_WEEK} |
| Tool events (24h) | ${EVENTS_TODAY} |
| Reusable prompts flagged (7d) | ${REUSABLE_PROMPTS} |
| Open bugs | ${OPEN_BUGS} |
| Session candidates in AIOS | ${CANDIDATES} |
| AI history imported | ${AI_IMPORTED} |
| AI history staged (pending review) | ${AI_STAGED} |
| AI history deferred | ${AI_DEFERRED} |
```

- [ ] **Step 4: Test the health check**

```bash
bash ~/ai-os/scripts/health_check.sh
```

Expected: runs without error, Obsidian dashboard shows new rows, macOS notification fires.

- [ ] **Step 5: Commit**

```bash
cd ~/AIOS
git add ../ai-os/scripts/health_check.sh
git commit -m "feat: add AI history import stats to health check dashboard"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Covered by |
|---|---|
| Importing ChatGPT exports | Tasks 5, 6, 7 |
| Importing Claude exports | Task 10 |
| Importing Codex session history | Task 11 |
| Markdown notes with frontmatter | Task 5 (render_markdown) |
| `type: ai-history` isolation | Task 5 (tests explicitly check forbidden fields) |
| `why_it_mattered` section | Task 5 (render_markdown includes `## Why This Mattered`) |
| Staging outside vault | Tasks 3, 6 (READY_DIR) |
| Review gate before promotion | Tasks 8, 9 |
| SQLite batch tracking | Tasks 3, 6 |
| Deduplication | Task 12 |
| Quality scoring (deferred) | Tasks 5, 10, 11 |
| Vault folder structure | Task 2 |
| Open Actions dashboard fix | Task 1 |
| Batch synthesis note | Task 9 (promote-imports.sh scaffolds _Batch-{id}.md) |
| Health check integration | Task 13 |
| Entity candidate flagging | Task 8 (review-imports.sh reports repeated topic tags derived from title + first exchange) |
| `deferred` ≠ `rejected` | Task 6 (CLI never writes `rejected`; only humans do) |

Phase 3 (`resurface.sh`) is intentionally out of scope for this plan.

### Placeholder scan

One intentional real-data dependency remains: Task 11 derives the Codex fixture and parser from actual local Codex rollout/session data rather than inventing an unsupported shape.

### Type consistency

- `conv` dict structure defined in Task 5 (`parse_chatgpt_conversation`) and used identically in Task 6 (`render_markdown`) and Task 6 CLI
- `quality` values are `"keep"` / `"deferred"` throughout — consistent between module, CLI, shell scripts, and SQLite
- `status` values are `"staged"` / `"promoted"` / `"rejected"` throughout
- Batch ID format `YYYYMMDDHHMMSS--source` used consistently in CLI `make_batch_id()`, review script, and promote script
