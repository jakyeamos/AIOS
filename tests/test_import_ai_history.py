"""
Tests for import-ai-history.py

Run from the repository root:
    python3 -m pytest tests/test_import_ai_history.py -v
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"

# Allow importing from ./bin without assuming the repo lives at ~/AIOS.
sys.path.insert(0, str(ROOT / "bin"))


@pytest.fixture
def chatgpt_sample():
    with open(FIXTURES / "chatgpt_sample.json") as f:
        return json.load(f)


@pytest.fixture
def claude_sample():
    with open(FIXTURES / "claude_sample.json") as f:
        return json.load(f)


@pytest.fixture
def codex_sample():
    with open(FIXTURES / "codex_sample.json") as f:
        return json.load(f)


@pytest.fixture
def chatgpt_substantive(chatgpt_sample):
    return chatgpt_sample[0]


@pytest.fixture
def chatgpt_trivial(chatgpt_sample):
    return chatgpt_sample[1]


def test_slug_basic():
    from import_ai_history import title_to_slug

    assert (
        title_to_slug("Context Windows and Retrieval Tradeoffs") == "context-windows-and-retrieval"
    )


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


def test_slug_falls_back_for_symbol_only_titles():
    from import_ai_history import title_to_slug

    assert title_to_slug("!!!") == "untitled"


def test_id_is_deterministic():
    from import_ai_history import make_id

    assert make_id("chatgpt", "conv-123", "2024-01-01", "Test") == make_id(
        "chatgpt", "conv-123", "2024-01-01", "Test"
    )


def test_id_differs_by_source():
    from import_ai_history import make_id

    assert make_id("chatgpt", "conv-123", "2024-01-01", "Test") != make_id(
        "claude", "conv-123", "2024-01-01", "Test"
    )


def test_id_is_12_chars():
    from import_ai_history import make_id

    assert len(make_id("chatgpt", "conv-123", "2024-01-01", "Test")) == 12


def test_id_differs_by_source_native_id():
    from import_ai_history import make_id

    assert make_id("chatgpt", "conv-aaa", "2024-01-01", "Test") != make_id(
        "chatgpt", "conv-bbb", "2024-01-01", "Test"
    )


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


def test_quality_keep_sufficient_exchanges_and_words():
    from import_ai_history import score_quality

    exchanges = [
        {"question": "How does X work?", "answer": "X works by " + "word " * 55},
        {"question": "What about Y?", "answer": "Y is different because " + "word " * 55},
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


def test_quality_ignores_incomplete_trailing_question():
    from import_ai_history import score_quality

    exchanges = [
        {"question": "Q1", "answer": "word " * 120},
        {"question": "Q2", "answer": ""},
    ]
    assert score_quality(exchanges) == "deferred"


def test_chatgpt_messages_ordered_by_time():
    from import_ai_history import parse_chatgpt_messages

    mapping = {
        "n1": {
            "message": {
                "author": {"role": "user"},
                "content": {"parts": ["First"]},
                "create_time": 1.0,
            }
        },
        "n2": {
            "message": {
                "author": {"role": "assistant"},
                "content": {"parts": ["Response"]},
                "create_time": 2.0,
            }
        },
        "n3": {
            "message": {
                "author": {"role": "user"},
                "content": {"parts": ["Second"]},
                "create_time": 3.0,
            }
        },
    }
    msgs = parse_chatgpt_messages(mapping)
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    assert msgs[0]["text"] == "First"


def test_chatgpt_messages_skips_system_and_empty():
    from import_ai_history import parse_chatgpt_messages

    mapping = {
        "sys": {
            "message": {
                "author": {"role": "system"},
                "content": {"parts": [""]},
                "create_time": 0.0,
            }
        },
        "u1": {
            "message": {"author": {"role": "user"}, "content": {"parts": ["Q"]}, "create_time": 1.0}
        },
    }
    msgs = parse_chatgpt_messages(mapping)
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"


def test_chatgpt_messages_support_dict_parts():
    from import_ai_history import parse_chatgpt_messages

    mapping = {
        "u1": {
            "message": {
                "author": {"role": "user"},
                "content": {"parts": [{"text": "How does this work?"}]},
                "create_time": 1.0,
            }
        }
    }
    msgs = parse_chatgpt_messages(mapping)
    assert msgs[0]["text"] == "How does this work?"


def test_messages_to_exchanges_pairs_correctly():
    from import_ai_history import messages_to_exchanges

    messages = [
        {"role": "user", "text": "Q1", "time": 1},
        {"role": "assistant", "text": "A1", "time": 2},
        {"role": "user", "text": "Q2", "time": 3},
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


def test_claude_invalid_date_falls_back_deterministically():
    from import_ai_history import parse_claude_conversation

    raw = {
        "uuid": "claude-1",
        "name": "Bad date",
        "created_at": "not-a-date",
        "chat_messages": [],
    }
    conv = parse_claude_conversation(raw, "test-batch")
    assert conv["date"] == "1970-01-01"


def test_claude_parse_handles_capitalized_sender():
    from import_ai_history import parse_claude_conversation

    raw = {
        "uuid": "test",
        "name": "Sender Variant",
        "created_at": "2025-01-10T10:00:00+00:00",
        "chat_messages": [
            {
                "uuid": "m1",
                "text": "Q1",
                "content": [{"type": "text", "text": "Q1"}],
                "sender": "User",
                "created_at": "2025-01-10T10:00:00+00:00",
            },
            {
                "uuid": "m2",
                "text": "A1 " + "word " * 60,
                "content": [{"type": "text", "text": "A1 " + "word " * 60}],
                "sender": "Assistant",
                "created_at": "2025-01-10T10:01:00+00:00",
            },
            {
                "uuid": "m3",
                "text": "Q2",
                "content": [{"type": "text", "text": "Q2"}],
                "sender": "User",
                "created_at": "2025-01-10T10:02:00+00:00",
            },
            {
                "uuid": "m4",
                "text": "A2 " + "word " * 60,
                "content": [{"type": "text", "text": "A2 " + "word " * 60}],
                "sender": "Assistant",
                "created_at": "2025-01-10T10:03:00+00:00",
            },
        ],
    }
    conv = parse_claude_conversation(raw, "test-batch")
    assert conv["quality"] == "keep"


def test_load_codex_export_reads_directory_snapshot(tmp_path):
    from import_ai_history import load_codex_export

    session_id = "019d4ad3-d7ae-7a32-a3f9-1b3cfb9cdb00"
    (tmp_path / "session_index.jsonl").write_text(
        json.dumps({"id": session_id, "thread_name": "Assess test coverage"}) + "\n",
        encoding="utf-8",
    )
    rollout_path = (
        tmp_path / "rollout-2026-04-01T16-54-50-019d4ad3-d7ae-7a32-a3f9-1b3cfb9cdb00.jsonl"
    )
    rollout_lines = [
        {
            "type": "session_meta",
            "payload": {
                "id": session_id,
                "timestamp": "2026-04-01T20:54:50.554Z",
                "source": "vscode",
                "model_provider": "openai",
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "developer",
                "content": [{"type": "input_text", "text": "ignore developer"}],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Assess the tests"}],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "phase": "final_answer",
                "content": [
                    {"type": "output_text", "text": "The tests are broad but not complete."}
                ],
            },
        },
    ]
    rollout_path.write_text(
        "\n".join(json.dumps(line) for line in rollout_lines) + "\n", encoding="utf-8"
    )

    loaded = load_codex_export(str(tmp_path))
    assert len(loaded) == 1
    assert loaded[0]["title"] == "Assess test coverage"
    assert loaded[0]["messages"][0]["role"] == "user"
    assert loaded[0]["messages"][1]["phase"] == "final_answer"


def test_codex_parse_structure(codex_sample):
    from import_ai_history import parse_codex_conversation

    conv = parse_codex_conversation(codex_sample[0], "test-batch")
    assert conv["source"] == "codex"
    assert conv["batch_id"] == "test-batch"
    assert conv["title"] == "Assess test coverage"
    assert "ai-history/codex" in conv["tags"]
    assert len(conv["slug"]) > 0
    assert [message["role"] for message in conv["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_codex_parse_filters_setup_and_commentary():
    from import_ai_history import parse_codex_conversation

    raw = {
        "session_id": "codex-1",
        "title": "",
        "created_at": "2026-04-01T20:54:50.554Z",
        "source": "vscode",
        "model_provider": "openai",
        "messages": [
            {"role": "user", "phase": "none", "text": "# AGENTS.md instructions for /tmp/repo"},
            {
                "role": "user",
                "phase": "none",
                "text": "<environment_context>...</environment_context>",
            },
            {"role": "user", "phase": "none", "text": "Summarize the import plan"},
            {"role": "assistant", "phase": "commentary", "text": "I am opening the file now."},
            {
                "role": "assistant",
                "phase": "final_answer",
                "text": "The plan is strong but needs filename disambiguation.",
            },
        ],
    }
    conv = parse_codex_conversation(raw, "test-batch")
    assert conv["title"] == "Summarize the import plan"
    assert conv["key_exchanges"][0]["question"] == "Summarize the import plan"
    assert "opening the file now" not in conv["summary"].lower()


def test_make_id_collision_on_same_conversation(chatgpt_sample):
    from import_ai_history import parse_chatgpt_conversation

    conv1 = parse_chatgpt_conversation(chatgpt_sample[0], "batch-a")
    conv2 = parse_chatgpt_conversation(chatgpt_sample[0], "batch-b")
    assert conv1["id"] == conv2["id"]


def test_make_id_uses_source_native_id_for_same_title_same_day():
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


def test_markdown_has_required_sections(chatgpt_substantive):
    from import_ai_history import parse_chatgpt_conversation, render_markdown

    conv = parse_chatgpt_conversation(chatgpt_substantive, "test-batch")
    md = render_markdown(conv)
    for section in (
        "type: ai-history",
        "## Summary",
        "## Why This Mattered",
        "## Key Exchanges",
        "## Notes",
    ):
        assert section in md


def test_markdown_no_forbidden_frontmatter_fields(chatgpt_substantive):
    from import_ai_history import parse_chatgpt_conversation, render_markdown

    conv = parse_chatgpt_conversation(chatgpt_substantive, "test-batch")
    md = render_markdown(conv)
    for field in (
        "status:",
        "project:",
        "priority:",
        "due:",
        "outcome_score:",
        "reusable_candidate:",
    ):
        assert field not in md


def test_markdown_type_is_ai_history(chatgpt_substantive):
    from import_ai_history import parse_chatgpt_conversation, render_markdown

    conv = parse_chatgpt_conversation(chatgpt_substantive, "test-batch")
    md = render_markdown(conv)
    assert "type: ai-history" in md
    assert "type: session" not in md
    assert "type: project" not in md


def test_markdown_escapes_title_for_yaml():
    from import_ai_history import render_markdown

    conv = {
        "source": "chatgpt",
        "model": 'gpt-"test"',
        "date": "2024-03-15",
        "title": 'He said "quote"',
        "slug": "he-said-quote",
        "tags": ["ai-history/chatgpt"],
        "batch_id": "20260401104530--chatgpt",
        "quality": "keep",
        "summary": "summary",
        "key_exchanges": [{"question": "Q", "answer": "A"}],
    }
    md = render_markdown(conv)
    assert 'title: "He said \\"quote\\""' in md
    assert 'model: "gpt-\\"test\\""' in md


# --- Claude Code parser ---


def _make_cc_raw(
    *,
    session_id="cc-sess-1",
    created_at="2026-04-01T20:00:00.000Z",
    project_dir="-Users-jakyeamos-Desktop-Fantasy",
    model="claude-sonnet-4-6",
    messages=None,
):
    return {
        "session_id": session_id,
        "created_at": created_at,
        "cwd": "/Users/jakyeamos/Desktop/Fantasy",
        "model": model,
        "project_dir": project_dir,
        "messages": messages or [],
    }


def _cc_messages_substantive():
    """Two complete Q&A pairs with enough words to qualify as 'keep'."""
    return [
        {
            "role": "user",
            "text": "How should I structure my dynasty trade value rankings?",
            "time": 1.0,
        },
        {
            "role": "assistant",
            "text": "Dynasty trade values depend on age, position scarcity, and team context. "
            + "word " * 55,
            "time": 2.0,
        },
        {
            "role": "user",
            "text": "What about rookie picks versus established players?",
            "time": 3.0,
        },
        {
            "role": "assistant",
            "text": "Rookie picks carry option value but are volatile. " + "word " * 55,
            "time": 4.0,
        },
    ]


def test_strip_claude_code_scaffolding_removes_caveat():
    from import_ai_history import strip_claude_code_scaffolding

    text = "<local-command-caveat>DO NOT respond to these messages</local-command-caveat> actual content"
    assert strip_claude_code_scaffolding(text) == "actual content"


def test_strip_claude_code_scaffolding_removes_system_reminder():
    from import_ai_history import strip_claude_code_scaffolding

    text = "before <system-reminder>\nsome injected context\n</system-reminder> after"
    result = strip_claude_code_scaffolding(text)
    assert "system-reminder" not in result
    assert "before" in result
    assert "after" in result


def test_strip_claude_code_scaffolding_leaves_real_text():
    from import_ai_history import strip_claude_code_scaffolding

    text = "How do I structure the trade rankings for this season?"
    assert strip_claude_code_scaffolding(text) == text


def test_strip_claude_code_scaffolding_empty_after_stripping():
    from import_ai_history import strip_claude_code_scaffolding

    text = "<command-name>/clear</command-name><command-message>clear</command-message><command-args></command-args>"
    assert strip_claude_code_scaffolding(text) == ""


def test_cwd_to_project_tag_home():
    from import_ai_history import cwd_to_project_tag

    assert cwd_to_project_tag("-Users-jakyeamos") == "project/home"


def test_cwd_to_project_tag_project():
    from import_ai_history import cwd_to_project_tag

    assert cwd_to_project_tag("-Users-jakyeamos-Desktop-Fantasy") == "project/desktop-fantasy"
    assert (
        cwd_to_project_tag("-Users-jakyeamos-Downloads-soundscape-app")
        == "project/downloads-soundscape-app"
    )


def test_claude_code_parse_structure():
    from import_ai_history import parse_claude_code_conversation

    raw = _make_cc_raw(messages=_cc_messages_substantive())
    conv = parse_claude_code_conversation(raw, "test-batch")
    assert conv["source"] == "claude-code"
    assert conv["date"] == "2026-04-01"
    assert conv["batch_id"] == "test-batch"
    assert "ai-history/claude-code" in conv["tags"]
    assert "project/desktop-fantasy" in conv["tags"]
    assert len(conv["key_exchanges"]) > 0
    assert len(conv["slug"]) > 0


def test_claude_code_injects_project_tag_second():
    from import_ai_history import parse_claude_code_conversation

    raw = _make_cc_raw(messages=_cc_messages_substantive())
    conv = parse_claude_code_conversation(raw, "test-batch")
    assert conv["tags"][0] == "ai-history/claude-code"
    assert conv["tags"][1] == "project/desktop-fantasy"


def test_claude_code_title_from_first_user_message():
    from import_ai_history import parse_claude_code_conversation

    raw = _make_cc_raw(messages=_cc_messages_substantive())
    conv = parse_claude_code_conversation(raw, "test-batch")
    assert "dynasty trade" in conv["title"].lower()


def test_claude_code_title_truncated_at_word_boundary():
    from import_ai_history import parse_claude_code_conversation

    long_msg = "word " * 30
    raw = _make_cc_raw(
        messages=[
            {"role": "user", "text": long_msg, "time": 1.0},
            {"role": "assistant", "text": "answer " * 60, "time": 2.0},
            {"role": "user", "text": "follow up?", "time": 3.0},
            {"role": "assistant", "text": "response " * 60, "time": 4.0},
        ]
    )
    conv = parse_claude_code_conversation(raw, "test-batch")
    assert len(conv["title"]) <= 80
    assert not conv["title"].endswith(" ")


def test_claude_code_scaffolding_filtered_from_exchanges():
    from import_ai_history import parse_claude_code_conversation

    raw = _make_cc_raw(
        messages=[
            {
                "role": "user",
                "text": "<command-name>/clear</command-name><command-message>clear</command-message>",
                "time": 1.0,
            },
            {"role": "user", "text": "How do I model position scarcity in dynasty?", "time": 2.0},
            {"role": "assistant", "text": "Position scarcity drives " + "value " * 60, "time": 3.0},
            {"role": "user", "text": "What positions are scarcest?", "time": 4.0},
            {
                "role": "assistant",
                "text": "Wide receiver depth is the thinnest. " + "word " * 55,
                "time": 5.0,
            },
        ]
    )
    conv = parse_claude_code_conversation(raw, "test-batch")
    assert conv["quality"] == "keep"
    first_q = conv["key_exchanges"][0]["question"]
    assert "command-name" not in first_q
    assert "clear" not in first_q.lower()


def test_claude_code_substantive_is_keep():
    from import_ai_history import parse_claude_code_conversation

    raw = _make_cc_raw(messages=_cc_messages_substantive())
    conv = parse_claude_code_conversation(raw, "test-batch")
    assert conv["quality"] == "keep"


def test_claude_code_trivial_is_deferred():
    from import_ai_history import parse_claude_code_conversation

    raw = _make_cc_raw(
        messages=[
            {"role": "user", "text": "hi", "time": 1.0},
            {"role": "assistant", "text": "Hello!", "time": 2.0},
        ]
    )
    conv = parse_claude_code_conversation(raw, "test-batch")
    assert conv["quality"] == "deferred"


def test_claude_code_model_extracted():
    from import_ai_history import parse_claude_code_conversation

    raw = _make_cc_raw(model="claude-sonnet-4-6", messages=_cc_messages_substantive())
    conv = parse_claude_code_conversation(raw, "test-batch")
    assert conv["model"] == "claude-sonnet-4-6"


def test_load_claude_code_export_walks_project_dirs(tmp_path):
    from import_ai_history import load_claude_code_export

    proj_dir = tmp_path / "-Users-jakyeamos-Desktop-Fantasy"
    proj_dir.mkdir()
    session_file = proj_dir / "abc12345-0000-0000-0000-000000000000.jsonl"
    events = [
        {
            "type": "user",
            "isMeta": False,
            "isSidechain": False,
            "timestamp": "2026-04-01T10:00:00.000Z",
            "cwd": "/Users/jakyeamos/Desktop/Fantasy",
            "sessionId": "abc12345-0000-0000-0000-000000000000",
            "message": {"role": "user", "content": "How do I score WR positional scarcity?"},
        },
        {
            "type": "assistant",
            "isMeta": False,
            "isSidechain": False,
            "timestamp": "2026-04-01T10:00:01.000Z",
            "cwd": "/Users/jakyeamos/Desktop/Fantasy",
            "sessionId": "abc12345-0000-0000-0000-000000000000",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-6",
                "content": [{"type": "text", "text": "WR scarcity is driven by " + "depth " * 60}],
            },
        },
        {
            "type": "user",
            "isMeta": False,
            "isSidechain": False,
            "timestamp": "2026-04-01T10:00:02.000Z",
            "cwd": "/Users/jakyeamos/Desktop/Fantasy",
            "sessionId": "abc12345-0000-0000-0000-000000000000",
            "message": {"role": "user", "content": "What about TE premium leagues?"},
        },
        {
            "type": "assistant",
            "isMeta": False,
            "isSidechain": False,
            "timestamp": "2026-04-01T10:00:03.000Z",
            "cwd": "/Users/jakyeamos/Desktop/Fantasy",
            "sessionId": "abc12345-0000-0000-0000-000000000000",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-6",
                "content": [
                    {
                        "type": "text",
                        "text": "TE premium leagues inflate TE values. " + "word " * 55,
                    }
                ],
            },
        },
    ]
    session_file.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")

    sessions = load_claude_code_export(str(tmp_path))
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "abc12345-0000-0000-0000-000000000000"
    assert sessions[0]["project_dir"] == "-Users-jakyeamos-Desktop-Fantasy"
    assert sessions[0]["model"] == "claude-sonnet-4-6"
    assert len(sessions[0]["messages"]) == 4


def test_load_claude_code_export_skips_observer_sessions(tmp_path):
    from import_ai_history import load_claude_code_export

    obs_dir = tmp_path / "-Users-jakyeamos--claude-mem-observer-sessions"
    obs_dir.mkdir()
    (obs_dir / "obs-session.jsonl").write_text(
        json.dumps(
            {
                "type": "user",
                "isMeta": False,
                "isSidechain": False,
                "timestamp": "2026-04-01T10:00:00Z",
                "message": {"role": "user", "content": "observe"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    sessions = load_claude_code_export(str(tmp_path))
    assert len(sessions) == 0


def test_load_claude_code_export_skips_meta_events(tmp_path):
    from import_ai_history import load_claude_code_export

    proj_dir = tmp_path / "-Users-jakyeamos"
    proj_dir.mkdir()
    session_file = proj_dir / "sess-0000-0000-0000-000000000000.jsonl"
    events = [
        {
            "type": "user",
            "isMeta": True,
            "isSidechain": False,
            "timestamp": "2026-04-01T10:00:00Z",
            "message": {"role": "user", "content": "Base directory for this skill: /path/to/skill"},
        },
        {
            "type": "user",
            "isMeta": False,
            "isSidechain": False,
            "timestamp": "2026-04-01T10:00:01Z",
            "message": {"role": "user", "content": "What is the best approach for this refactor?"},
        },
        {
            "type": "assistant",
            "isMeta": False,
            "isSidechain": False,
            "timestamp": "2026-04-01T10:00:02Z",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-6",
                "content": [{"type": "text", "text": "The best approach is " + "word " * 60}],
            },
        },
        {
            "type": "user",
            "isMeta": False,
            "isSidechain": False,
            "timestamp": "2026-04-01T10:00:03Z",
            "message": {"role": "user", "content": "How do I apply that pattern?"},
        },
        {
            "type": "assistant",
            "isMeta": False,
            "isSidechain": False,
            "timestamp": "2026-04-01T10:00:04Z",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-6",
                "content": [{"type": "text", "text": "Apply it by " + "word " * 60}],
            },
        },
    ]
    session_file.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")

    sessions = load_claude_code_export(str(tmp_path))
    assert len(sessions) == 1
    texts = [m["text"] for m in sessions[0]["messages"] if m["role"] == "user"]
    assert not any("Base directory" in t for t in texts)
    assert any("refactor" in t for t in texts)
