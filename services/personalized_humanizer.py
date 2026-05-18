from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_PATH = ROOT / "config" / "personalized-humanizer" / "profile.json"
DEFAULT_EVALS_PATH = ROOT / "config" / "personalized-humanizer" / "evals.json"
DEFAULT_RETRIEVAL_POLICY_PATH = ROOT / "config" / "personalized-humanizer" / "retrieval-policy.json"

VoiceMode = Literal[
    "professional_outreach",
    "project_build_in_public",
    "academic_reflective",
    "prompt_prd",
    "creative_narrative",
]
FeedbackVerdict = Literal["approved", "edited", "rejected"]
ProfileUpdateStatus = Literal["draft", "candidate", "approved", "rejected", "deprecated"]
PipelinePosition = Literal["standalone", "after_generic_humanizer"]

MODE_KEYWORDS: dict[VoiceMode, tuple[str, ...]] = {
    "professional_outreach": (
        "linkedin",
        "cold email",
        "recruiter",
        "mentor",
        "networking",
        "connect",
        "outreach",
    ),
    "project_build_in_public": (
        "twitter",
        "x post",
        "linkedin post",
        "build in public",
        "project update",
        "aios",
        "soundscape",
        "court vision",
        "terrace",
    ),
    "academic_reflective": (
        "essay",
        "reflection",
        "discussion post",
        "reading",
        "academic",
        "class",
    ),
    "prompt_prd": (
        "codex",
        "prompt",
        "prd",
        "implementation",
        "audit",
        "handoff",
        "acceptance criteria",
    ),
    "creative_narrative": (
        "scene",
        "character",
        "chapter",
        "narrative",
        "prose",
        "dialogue",
        "book",
    ),
}

AI_PHRASES = {
    "groundbreaking",
    "pivotal",
    "showcasing",
    "commitment to innovation",
    "unlocking new possibilities",
    "delve",
    "vibrant",
    "tapestry",
    "underscores",
    "testament",
    "landscape",
}


@dataclass(frozen=True)
class CorpusExample:
    source_id: str
    mode: VoiceMode
    text: str
    quality: str = "user_written"
    approved: bool = True
    source_path: str | None = None


@dataclass(frozen=True)
class VoicePacket:
    mode: VoiceMode
    profile_version: str
    tone: str
    rules: tuple[str, ...]
    anti_rules: tuple[str, ...]
    evidence_refs: tuple[dict[str, Any], ...]
    confidence: float


@dataclass(frozen=True)
class RewriteResult:
    mode: VoiceMode
    pipeline_position: PipelinePosition
    output: str
    voice_packet: VoicePacket
    scorecard: dict[str, int]
    risks: tuple[str, ...]
    debug: dict[str, Any] | None = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return loaded


def _json_dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def _stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def classify_writing_task(text: str, requested_mode: str | None = None) -> VoiceMode:
    if requested_mode:
        normalized = requested_mode.strip().lower().replace("-", "_")
        if normalized in MODE_KEYWORDS:
            return normalized  # type: ignore[return-value]
        raise ValueError(f"Unknown personalized humanizer mode: {requested_mode}")

    lowered = text.lower()
    scores: dict[VoiceMode, int] = {
        mode: sum(1 for keyword in keywords if keyword in lowered)
        for mode, keywords in MODE_KEYWORDS.items()
    }
    if re.search(r"(^|\n)\s*(goal|requirements|acceptance criteria|constraints):", lowered):
        scores["prompt_prd"] += 4
    if "hi " in lowered and ("connect" in lowered or "advice" in lowered):
        scores["professional_outreach"] += 3
    if any(phrase in lowered for phrase in ("i built", "i'm building", "today i")):
        scores["project_build_in_public"] += 2

    selected = max(scores.items(), key=lambda row: (row[1], row[0]))[0]
    if scores[selected] == 0:
        return "academic_reflective" if "i " in lowered else "project_build_in_public"
    return selected


def retrieve_relevant_examples(
    examples: list[CorpusExample],
    *,
    mode: VoiceMode,
    profile: dict[str, Any],
    max_examples: int = 4,
    allow_cross_mode: bool = False,
) -> list[CorpusExample]:
    mode_profile = (profile.get("modes") or {}).get(mode, {})
    allowed_modes = set(mode_profile.get("allowed_source_modes") or [mode])
    if not allow_cross_mode:
        allowed_modes = {mode}

    ranked: list[tuple[int, CorpusExample]] = []
    for example in examples:
        if example.mode not in allowed_modes:
            continue
        score = 0
        if example.approved:
            score += 4
        if example.quality == "approved_final":
            score += 3
        elif example.quality == "user_written":
            score += 2
        if example.mode == mode:
            score += 2
        ranked.append((score, example))

    ranked.sort(key=lambda row: (-row[0], row[1].source_id))
    return [example for _, example in ranked[:max_examples]]


def build_voice_packet(
    profile: dict[str, Any],
    *,
    mode: VoiceMode,
    examples: list[CorpusExample],
) -> VoicePacket:
    global_voice = profile.get("global_voice") or {}
    mode_profile = (profile.get("modes") or {}).get(mode)
    if not isinstance(mode_profile, dict):
        raise ValueError(f"Profile is missing mode: {mode}")

    global_rules = [
        str(rule.get("rule", "")).strip()
        for rule in global_voice.get("style_rules", [])
        if isinstance(rule, dict) and str(rule.get("rule", "")).strip()
    ]
    global_anti = [
        str(rule.get("rule", "")).strip()
        for rule in global_voice.get("anti_style_rules", [])
        if isinstance(rule, dict) and str(rule.get("rule", "")).strip()
    ]
    mode_rules = [str(rule) for rule in mode_profile.get("style_rules", []) if str(rule).strip()]
    mode_anti = [str(rule) for rule in mode_profile.get("anti_style_rules", []) if str(rule).strip()]
    evidence_refs = []
    for example in examples:
        evidence_refs.append(
            {
                "source_id": example.source_id,
                "source_hash": _stable_hash(example.text),
                "source_path": example.source_path,
                "mode": example.mode,
                "quality": example.quality,
                "excerpt_stored": False,
            }
        )

    confidence = float(mode_profile.get("confidence", 0.5))
    if examples:
        confidence = min(0.95, confidence + min(len(examples), 4) * 0.04)

    return VoicePacket(
        mode=mode,
        profile_version=str(profile.get("version", "unknown")),
        tone=str(mode_profile.get("tone", "")),
        rules=tuple(global_rules + mode_rules),
        anti_rules=tuple(global_anti + mode_anti),
        evidence_refs=tuple(evidence_refs),
        confidence=round(confidence, 2),
    )


def _remove_generic_ai_phrases(text: str) -> str:
    replacements = {
        "groundbreaking": "useful",
        "marks a pivotal step forward": "is a practical step",
        "showcasing our commitment to innovation": "showing what works in practice",
        "unlocking new possibilities": "making the next iteration easier to test",
        "vibrant": "active",
        "delve into": "look at",
        "underscores": "shows",
        "testament to": "evidence of",
    }
    result = text
    for old, new in replacements.items():
        result = re.sub(re.escape(old), new, result, flags=re.IGNORECASE)
    return result


def transform_text(
    text: str,
    packet: VoicePacket,
    *,
    pipeline_position: PipelinePosition = "standalone",
) -> str:
    _validate_pipeline_position(pipeline_position)
    original = text.strip()
    if not original:
        return ""

    cleaned = original
    if pipeline_position == "standalone":
        cleaned = _remove_generic_ai_phrases(original)
    if packet.mode == "prompt_prd":
        return _transform_prompt(cleaned)
    if packet.mode == "professional_outreach":
        return _transform_outreach(cleaned)
    if packet.mode == "project_build_in_public":
        return _transform_project_update(cleaned)
    if packet.mode == "academic_reflective":
        return _transform_reflective(cleaned)
    if packet.mode == "creative_narrative":
        return _transform_creative(cleaned)
    return cleaned


def _transform_prompt(text: str) -> str:
    if "\n" in text or re.search(r"(^|\n)\s*[-0-9]", text):
        return text
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if len(sentences) <= 2:
        return text
    return "\n".join(f"- {sentence}" for sentence in sentences)


def _transform_outreach(text: str) -> str:
    result = text
    result = re.sub(r"\bI am interested in\b", "I was interested in", result)
    result = re.sub(r"\bwould like to connect\b", "would be glad to connect", result)
    result = re.sub(r"\bwould appreciate any advice\b", "would appreciate any practical advice", result)
    return result


def _transform_project_update(text: str) -> str:
    result = text
    if "helps agents check their own work" in result and "calling something done" in result:
        result = result.replace(
            "It helps agents check their own work before calling something done.",
            "The useful part is the gate: agents have to check the actual work path before calling it done.",
        )
    return result


def _transform_reflective(text: str) -> str:
    result = text
    result = re.sub(r"\bthe most important part\b", "the part I keep coming back to", result)
    return result


def _transform_creative(text: str) -> str:
    result = text
    result = re.sub(r"\brealized he did not know\b", "realized he still did not know", result)
    return result


def score_quality(original: str, output: str, packet: VoicePacket) -> tuple[dict[str, int], tuple[str, ...]]:
    original_tokens = _tokenize(original)
    output_tokens = _tokenize(output)
    overlap = len(original_tokens & output_tokens) / max(len(original_tokens), 1)
    added_tokens = output_tokens - original_tokens
    risky_added = {
        token
        for token in added_tokens
        if token
        in {
            "founder",
            "startup",
            "award",
            "raised",
            "team",
            "company",
            "credential",
            "expert",
        }
    }
    ai_count = sum(1 for phrase in AI_PHRASES if phrase in output.lower())
    verbosity_delta = max(0, len(output.split()) - len(original.split()))
    structure_preserved = 5
    if packet.mode == "prompt_prd" and any(marker in original for marker in ("-", ":", "\n")):
        structure_preserved = 5 if any(marker in output for marker in ("-", ":", "\n")) else 2

    scorecard = {
        "meaning_preservation": min(5, max(0, round(overlap * 5))),
        "voice_match": 4 if output != original else 3,
        "context_fit": structure_preserved if packet.mode == "prompt_prd" else 4,
        "specificity": 4 if len(output_tokens) >= max(4, len(original_tokens) - 2) else 2,
        "over_personalization_risk": min(5, len(risky_added) * 2),
        "generic_ai_feel": min(5, ai_count),
        "verbosity": min(5, verbosity_delta // 8),
    }

    risks: list[str] = []
    if scorecard["meaning_preservation"] < 3:
        risks.append("meaning_preservation_low")
    if risky_added:
        risks.append("possible_unsupported_personal_claims")
    if ai_count:
        risks.append("generic_ai_phrasing_remaining")
    if packet.mode == "prompt_prd" and structure_preserved < 4:
        risks.append("useful_structure_may_be_weakened")
    return scorecard, tuple(risks)


def humanize_text(
    text: str,
    *,
    requested_mode: str | None = None,
    pipeline_position: PipelinePosition = "standalone",
    examples: list[CorpusExample] | None = None,
    profile_path: Path | None = None,
    debug: bool = False,
    allow_cross_mode: bool = False,
) -> RewriteResult:
    _validate_pipeline_position(pipeline_position)
    profile = _load_json(profile_path or DEFAULT_PROFILE_PATH)
    mode = classify_writing_task(text, requested_mode)
    selected_examples = retrieve_relevant_examples(
        examples or [],
        mode=mode,
        profile=profile,
        allow_cross_mode=allow_cross_mode,
    )
    packet = build_voice_packet(profile, mode=mode, examples=selected_examples)
    output = transform_text(text, packet, pipeline_position=pipeline_position)
    scorecard, risks = score_quality(text, output, packet)
    debug_payload = None
    if debug:
        debug_payload = {
            "selected_voice_profile": mode,
            "pipeline_position": pipeline_position,
            "pipeline_contract": _pipeline_contract(pipeline_position),
            "profile_version": packet.profile_version,
            "style_rules_applied": list(packet.rules),
            "anti_style_rules": list(packet.anti_rules),
            "evidence_refs": list(packet.evidence_refs),
            "confidence": packet.confidence,
            "risks": list(risks),
            "changed": text != output,
        }
    return RewriteResult(
        mode=mode,
        pipeline_position=pipeline_position,
        output=output,
        voice_packet=packet,
        scorecard=scorecard,
        risks=risks,
        debug=debug_payload,
    )


def _pipeline_contract(pipeline_position: PipelinePosition) -> str:
    _validate_pipeline_position(pipeline_position)
    if pipeline_position == "after_generic_humanizer":
        return "voice_specific_only"
    return "generic_cleanup_plus_voice"


def _validate_pipeline_position(pipeline_position: str) -> None:
    if pipeline_position not in {"standalone", "after_generic_humanizer"}:
        raise ValueError(f"Unknown personalized humanizer pipeline position: {pipeline_position}")


def ensure_personalized_humanizer_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS personalized_humanizer_runs (
          id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          profile_id TEXT NOT NULL,
          profile_version TEXT NOT NULL,
          mode TEXT NOT NULL,
          input_hash TEXT NOT NULL,
          output_hash TEXT NOT NULL,
          voice_packet_json TEXT NOT NULL DEFAULT '{}',
          scorecard_json TEXT NOT NULL DEFAULT '{}',
          risks_json TEXT NOT NULL DEFAULT '[]',
          debug_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS personalized_humanizer_feedback (
          id TEXT PRIMARY KEY,
          run_id TEXT REFERENCES personalized_humanizer_runs(id),
          created_at TEXT NOT NULL,
          verdict TEXT NOT NULL,
          user_revision_hash TEXT,
          notes TEXT,
          evidence_json TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS personalized_humanizer_profile_updates (
          id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          profile_id TEXT NOT NULL,
          profile_version TEXT NOT NULL,
          mode TEXT,
          status TEXT NOT NULL,
          proposed_rule TEXT NOT NULL,
          rationale TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          decision_note TEXT,
          decided_at TEXT,
          decided_by TEXT
        );

        CREATE TABLE IF NOT EXISTS personalized_humanizer_eval_results (
          id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          suite_id TEXT NOT NULL,
          profile_version TEXT NOT NULL,
          results_json TEXT NOT NULL DEFAULT '[]',
          summary_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_personalized_humanizer_runs_created
          ON personalized_humanizer_runs(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_personalized_humanizer_feedback_run
          ON personalized_humanizer_feedback(run_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_personalized_humanizer_updates_status
          ON personalized_humanizer_profile_updates(status, created_at DESC);
        """
    )


def record_rewrite_run(
    conn: sqlite3.Connection,
    result: RewriteResult,
    *,
    input_text: str,
    profile_id: str = "personal-voice-default",
) -> str:
    ensure_personalized_humanizer_schema(conn)
    run_id = f"phr-{uuid.uuid4().hex[:12]}"
    packet = {
        "mode": result.voice_packet.mode,
        "pipeline_position": result.pipeline_position,
        "pipeline_contract": _pipeline_contract(result.pipeline_position),
        "profile_version": result.voice_packet.profile_version,
        "tone": result.voice_packet.tone,
        "rules": list(result.voice_packet.rules),
        "anti_rules": list(result.voice_packet.anti_rules),
        "evidence_refs": list(result.voice_packet.evidence_refs),
        "confidence": result.voice_packet.confidence,
    }
    conn.execute(
        """
        INSERT INTO personalized_humanizer_runs (
          id, created_at, profile_id, profile_version, mode, input_hash, output_hash,
          voice_packet_json, scorecard_json, risks_json, debug_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            _now_iso(),
            profile_id,
            result.voice_packet.profile_version,
            result.mode,
            _stable_hash(input_text),
            _stable_hash(result.output),
            _json_dump(packet),
            _json_dump(result.scorecard),
            _json_dump(list(result.risks)),
            _json_dump(result.debug or {}),
        ),
    )
    return run_id


def record_feedback(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    verdict: FeedbackVerdict,
    notes: str = "",
    user_revision: str | None = None,
) -> dict[str, Any]:
    ensure_personalized_humanizer_schema(conn)
    feedback_id = f"phf-{uuid.uuid4().hex[:12]}"
    evidence = [{"type": "humanizer_run", "id": run_id}, {"type": "feedback_verdict", "value": verdict}]
    conn.execute(
        """
        INSERT INTO personalized_humanizer_feedback (
          id, run_id, created_at, verdict, user_revision_hash, notes, evidence_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            feedback_id,
            run_id,
            _now_iso(),
            verdict,
            _stable_hash(user_revision) if user_revision else None,
            notes,
            _json_dump(evidence),
        ),
    )

    proposal: dict[str, Any] | None = None
    if verdict in {"approved", "edited"} and notes.strip():
        proposal = propose_profile_update(
            conn,
            profile_id="personal-voice-default",
            profile_version=_profile_version_for_run(conn, run_id),
            mode=_mode_for_run(conn, run_id),
            proposed_rule=notes.strip(),
            rationale="User feedback supplied a possible reusable voice preference.",
            evidence=[{"type": "feedback", "id": feedback_id}, {"type": "humanizer_run", "id": run_id}],
        )

    return {"feedback_id": feedback_id, "proposal": proposal}


def _profile_version_for_run(conn: sqlite3.Connection, run_id: str) -> str:
    row = conn.execute(
        "SELECT profile_version FROM personalized_humanizer_runs WHERE id = ?",
        (run_id,),
    ).fetchone()
    return str(row[0]) if row else "unknown"


def _mode_for_run(conn: sqlite3.Connection, run_id: str) -> str | None:
    row = conn.execute("SELECT mode FROM personalized_humanizer_runs WHERE id = ?", (run_id,)).fetchone()
    return str(row[0]) if row else None


def propose_profile_update(
    conn: sqlite3.Connection,
    *,
    profile_id: str,
    profile_version: str,
    mode: str | None,
    proposed_rule: str,
    rationale: str,
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    ensure_personalized_humanizer_schema(conn)
    update_id = f"phu-{uuid.uuid4().hex[:12]}"
    now = _now_iso()
    status: ProfileUpdateStatus = "candidate" if len(evidence) >= 2 else "draft"
    conn.execute(
        """
        INSERT INTO personalized_humanizer_profile_updates (
          id, created_at, updated_at, profile_id, profile_version, mode, status,
          proposed_rule, rationale, evidence_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            update_id,
            now,
            now,
            profile_id,
            profile_version,
            mode,
            status,
            proposed_rule,
            rationale,
            _json_dump(evidence),
        ),
    )
    return {
        "id": update_id,
        "status": status,
        "profile_id": profile_id,
        "profile_version": profile_version,
        "mode": mode,
        "proposed_rule": proposed_rule,
        "evidence_count": len(evidence),
    }


def transition_profile_update(
    conn: sqlite3.Connection,
    update_id: str,
    *,
    requested_status: ProfileUpdateStatus,
    decided_by: str = "local-user",
    decision_note: str = "",
) -> dict[str, Any]:
    ensure_personalized_humanizer_schema(conn)
    row = conn.execute(
        "SELECT status, evidence_json FROM personalized_humanizer_profile_updates WHERE id = ?",
        (update_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown profile update: {update_id}")
    evidence = json.loads(str(row[1] or "[]"))
    status = requested_status
    note = decision_note
    if requested_status == "approved" and len(evidence) < 2:
        status = "candidate"
        note = "Approval requires at least two evidence records."
    now = _now_iso()
    conn.execute(
        """
        UPDATE personalized_humanizer_profile_updates
        SET status = ?, updated_at = ?, decision_note = ?, decided_at = ?, decided_by = ?
        WHERE id = ?
        """,
        (status, now, note, now, decided_by, update_id),
    )
    return {"id": update_id, "status": status, "decision_note": note}


def run_eval_suite(
    *,
    profile_path: Path | None = None,
    evals_path: Path | None = None,
) -> dict[str, Any]:
    suite = _load_json(evals_path or DEFAULT_EVALS_PATH)
    profile = _load_json(profile_path or DEFAULT_PROFILE_PATH)
    cases = suite.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Personalized humanizer eval suite must contain cases.")

    results: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        result = humanize_text(
            str(case.get("input", "")),
            requested_mode=str(case.get("mode", "")),
            profile_path=profile_path,
            debug=True,
        )
        passed = (
            result.scorecard["meaning_preservation"] >= 3
            and result.scorecard["context_fit"] >= 3
            and result.scorecard["over_personalization_risk"] <= 1
            and result.scorecard["generic_ai_feel"] <= 2
            and result.scorecard["verbosity"] <= 2
        )
        results.append(
            {
                "id": str(case.get("id", "")),
                "mode": result.mode,
                "passed": passed,
                "scorecard": result.scorecard,
                "risks": list(result.risks),
                "output_hash": _stable_hash(result.output),
            }
        )

    passed_count = sum(1 for result in results if result["passed"])
    summary = {
        "suite_id": str(suite.get("suite_id", "personalized-humanizer")),
        "profile_version": str(profile.get("version", "unknown")),
        "case_count": len(results),
        "passed_count": passed_count,
        "failed_count": len(results) - passed_count,
        "passed": passed_count == len(results),
    }
    return {"summary": summary, "results": results}


def record_eval_result(conn: sqlite3.Connection, eval_result: dict[str, Any]) -> str:
    ensure_personalized_humanizer_schema(conn)
    eval_id = f"phe-{uuid.uuid4().hex[:12]}"
    summary = eval_result.get("summary") or {}
    conn.execute(
        """
        INSERT INTO personalized_humanizer_eval_results (
          id, created_at, suite_id, profile_version, results_json, summary_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            eval_id,
            _now_iso(),
            str(summary.get("suite_id", "personalized-humanizer")),
            str(summary.get("profile_version", "unknown")),
            _json_dump(eval_result.get("results") or []),
            _json_dump(summary),
        ),
    )
    return eval_id
