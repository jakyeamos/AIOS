from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal

SignalType = Literal[
    "explicit_correction",
    "repeated_pattern",
    "approval",
    "command_repetition",
    "tool_friction",
    "context_miss",
    "model_mismatch",
    "contradiction",
]
RiskLevel = Literal["low", "medium", "high"]

CORRECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bdon'?t\s+(?P<body>[^.!?\n]+)", re.IGNORECASE),
    re.compile(r"\balways\s+(?P<body>[^.!?\n]+)", re.IGNORECASE),
    re.compile(r"\bnever\s+(?P<body>[^.!?\n]+)", re.IGNORECASE),
    re.compile(r"\bfrom now on[,]?\s+(?P<body>[^.!?\n]+)", re.IGNORECASE),
    re.compile(r"\bin this repo[,]?\s+(?P<body>[^.!?\n]+)", re.IGNORECASE),
)
APPROVAL_PATTERNS = (
    "approved",
    "looks good",
    "ship it",
    "accept all",
    "yes, do that",
    "that works",
)
SCOPE_RESTATEMENT_PATTERNS = (
    "that's not what i asked",
    "that is not what i asked",
    "the scope was",
    "stay in scope",
    "you changed the scope",
)
CONTEXT_MISS_PATTERNS = (
    "you missed the context",
    "missing context",
    "you didn't read",
    "you did not read",
    "irrelevant context",
    "loaded unrelated context",
)
SECOND_BRAIN_MISS_PATTERNS = (
    "second-brain miss",
    "second brain miss",
    "personal context was missing",
)
MODEL_MISMATCH_PATTERNS = (
    "wrong model",
    "model mismatch",
    "too weak model",
    "should have used a stronger model",
    "overkill model",
)


@dataclass(frozen=True)
class MetaLearningSignal:
    signal_id: str
    type: SignalType
    summary: str
    evidence: list[dict[str, str]]
    source_sessions: list[str]
    frequency: int
    recency: str | None
    confidence_points: list[str]
    recommended_target_layer: str
    risk_level: RiskLevel

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _Event:
    session_id: str
    kind: str
    summary: str
    text: str
    timestamp: str | None
    metadata: Mapping[str, Any]


def extract_meta_learning_signals(raw: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> list[MetaLearningSignal]:
    sessions = _normalize_sessions(raw)
    events: list[_Event] = []
    for session in sessions:
        events.extend(_events_from_session(session))

    signals: list[MetaLearningSignal] = []
    signals.extend(_explicit_correction_signals(events))
    signals.extend(_approval_signals(events))
    signals.extend(_command_repetition_signals(events))
    signals.extend(_tool_friction_signals(events))
    signals.extend(_context_miss_signals(events))
    signals.extend(_model_mismatch_signals(events))
    signals.extend(_scope_restatement_signals(events))
    signals.extend(_contradiction_signals(events))
    return sorted(signals, key=lambda signal: signal.signal_id)


def signals_to_dicts(signals: Iterable[MetaLearningSignal]) -> list[dict[str, Any]]:
    return [signal.to_dict() for signal in signals]


def _normalize_sessions(
    raw: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    if isinstance(raw, Mapping):
        if isinstance(raw.get("sessions"), list):
            return [item for item in raw["sessions"] if isinstance(item, Mapping)]
        return [raw]
    return [item for item in raw if isinstance(item, Mapping)]


def _events_from_session(session: Mapping[str, Any]) -> list[_Event]:
    session_id = str(session.get("session_id") or session.get("id") or "unknown-session")
    events: list[_Event] = []
    for index, message in enumerate(_list_of_mappings(session.get("messages"))):
        text = _text_from_mapping(message)
        if not text:
            continue
        events.append(
            _Event(
                session_id=session_id,
                kind=f"message:{message.get('role', 'unknown')}",
                summary=text[:160],
                text=text,
                timestamp=_optional_str(message.get("timestamp") or message.get("created_at")),
                metadata={"index": str(index), **{str(k): str(v) for k, v in message.items()}},
            )
        )
    for index, command in enumerate(_string_list(session.get("commands") or session.get("commands_run"))):
        events.append(
            _Event(
                session_id=session_id,
                kind="command",
                summary=command,
                text=command,
                timestamp=None,
                metadata={"index": str(index), "command": command},
            )
        )
    for index, item in enumerate(_list_of_mappings(session.get("tool_events") or session.get("tool_calls"))):
        text = _text_from_mapping(item) or str(item.get("command") or item.get("tool") or "")
        if not text:
            continue
        events.append(
            _Event(
                session_id=session_id,
                kind=str(item.get("type") or item.get("event_type") or "tool_event"),
                summary=text[:160],
                text=text,
                timestamp=_optional_str(item.get("timestamp") or item.get("created_at")),
                metadata={"index": str(index), **{str(k): str(v) for k, v in item.items()}},
            )
        )
    for index, item in enumerate(_list_of_mappings(session.get("context_events"))):
        text = _text_from_mapping(item) or str(item.get("summary") or item.get("type") or "")
        events.append(
            _Event(
                session_id=session_id,
                kind=str(item.get("type") or "context_event"),
                summary=text[:160],
                text=text,
                timestamp=_optional_str(item.get("timestamp") or item.get("created_at")),
                metadata={"index": str(index), **{str(k): str(v) for k, v in item.items()}},
            )
        )
    for index, item in enumerate(_list_of_mappings(session.get("model_events"))):
        text = _text_from_mapping(item) or str(item.get("summary") or item.get("type") or "")
        events.append(
            _Event(
                session_id=session_id,
                kind=str(item.get("type") or "model_event"),
                summary=text[:160],
                text=text,
                timestamp=_optional_str(item.get("timestamp") or item.get("created_at")),
                metadata={"index": str(index), **{str(k): str(v) for k, v in item.items()}},
            )
        )
    return events


def _explicit_correction_signals(events: list[_Event]) -> list[MetaLearningSignal]:
    signals: list[MetaLearningSignal] = []
    grouped: dict[str, list[_Event]] = defaultdict(list)
    for event in events:
        if not event.kind.startswith("message:user"):
            continue
        for correction in _corrections_from_text(event.text):
            grouped[_normalize_key(correction)].append(
                _Event(
                    session_id=event.session_id,
                    kind="explicit_correction",
                    summary=correction,
                    text=event.text,
                    timestamp=event.timestamp,
                    metadata=event.metadata,
                )
            )
    for key, group in grouped.items():
        signal_type: SignalType = "repeated_pattern" if len(group) > 1 else "explicit_correction"
        signals.append(
            _build_signal(
                signal_type,
                f"User correction: {group[0].summary}",
                group,
                ["explicit user correction", *_recurrence_points(group)],
                _target_layer_for_correction(group[0].summary),
                _risk_for_text(group[0].summary),
                stable_key=key,
            )
        )
    return signals


def _approval_signals(events: list[_Event]) -> list[MetaLearningSignal]:
    approvals = [
        event
        for event in events
        if event.kind.startswith("message:user")
        and any(pattern in event.text.lower() for pattern in APPROVAL_PATTERNS)
    ]
    return [
        _build_signal(
            "approval",
            "Repeated approval or acceptance language appeared in the session trace.",
            approvals,
            ["approval language observed", *_recurrence_points(approvals)],
            "observe_only",
            "low",
            stable_key="approval",
        )
    ] if approvals else []


def _command_repetition_signals(events: list[_Event]) -> list[MetaLearningSignal]:
    grouped = _group_repeated(events, kind="command")
    return [
        _build_signal(
            "command_repetition",
            f"Repeated command: {group[0].summary}",
            group,
            ["manual command repetition", *_recurrence_points(group)],
            "command_suggestion",
            "low",
            stable_key=f"command:{key}",
        )
        for key, group in grouped.items()
    ]


def _tool_friction_signals(events: list[_Event]) -> list[MetaLearningSignal]:
    friction = [
        event
        for event in events
        if "tool" in event.kind
        and any(token in _event_blob(event) for token in ("failed", "error", "retry", "blocked"))
    ]
    grouped = _group_by_summary(friction)
    return [
        _build_signal(
            "tool_friction",
            f"Repeated tool friction: {group[0].summary}",
            group,
            ["tool failure or retry evidence", *_recurrence_points(group)],
            "workflow_rule",
            "medium",
            stable_key=f"tool:{key}",
        )
        for key, group in grouped.items()
    ]


def _context_miss_signals(events: list[_Event]) -> list[MetaLearningSignal]:
    matched = [
        event
        for event in events
        if _matches_any(event.text, CONTEXT_MISS_PATTERNS + SECOND_BRAIN_MISS_PATTERNS)
        or event.kind in {"context_miss", "second_brain_miss", "irrelevant_context"}
    ]
    grouped = _group_by_summary(matched)
    return [
        _build_signal(
            "context_miss",
            f"Context miss: {group[0].summary}",
            group,
            ["context miss evidence", *_recurrence_points(group)],
            "context_packet_or_retrieval_policy",
            "medium",
            stable_key=f"context:{key}",
        )
        for key, group in grouped.items()
    ]


def _model_mismatch_signals(events: list[_Event]) -> list[MetaLearningSignal]:
    matched = [
        event
        for event in events
        if _matches_any(event.text, MODEL_MISMATCH_PATTERNS) or event.kind == "model_mismatch"
    ]
    grouped = _group_by_summary(matched)
    return [
        _build_signal(
            "model_mismatch",
            f"Model mismatch: {group[0].summary}",
            group,
            ["model mismatch evidence", *_recurrence_points(group)],
            "model_routing_policy",
            "medium",
            stable_key=f"model:{key}",
        )
        for key, group in grouped.items()
    ]


def _scope_restatement_signals(events: list[_Event]) -> list[MetaLearningSignal]:
    matched = [event for event in events if _matches_any(event.text, SCOPE_RESTATEMENT_PATTERNS)]
    grouped = _group_by_summary(matched)
    return [
        _build_signal(
            "repeated_pattern",
            f"Scope restatement: {group[0].summary}",
            group,
            ["scope restatement evidence", *_recurrence_points(group)],
            "workflow_rule",
            "medium",
            stable_key=f"scope:{key}",
        )
        for key, group in grouped.items()
    ]


def _contradiction_signals(events: list[_Event]) -> list[MetaLearningSignal]:
    directive_events: dict[str, list[_Event]] = defaultdict(list)
    for event in events:
        if not event.kind.startswith("message:user"):
            continue
        for directive, body in _directives_from_text(event.text):
            directive_events[_normalize_key(body)].append(
                _Event(
                    session_id=event.session_id,
                    kind=f"directive:{directive}",
                    summary=f"{directive} {body}",
                    text=event.text,
                    timestamp=event.timestamp,
                    metadata=event.metadata,
                )
            )
    signals: list[MetaLearningSignal] = []
    for key, group in directive_events.items():
        directives = {event.kind for event in group}
        if "directive:always" in directives and "directive:never" in directives:
            signals.append(
                _build_signal(
                    "contradiction",
                    f"Contradictory directives for: {group[0].summary}",
                    group,
                    ["conflicting always/never directives"],
                    "manual_review",
                    "high",
                    stable_key=f"contradiction:{key}",
                )
            )
    explicit = [event for event in events if event.kind == "contradiction"]
    if explicit:
        signals.append(
            _build_signal(
                "contradiction",
                f"Explicit contradiction: {explicit[0].summary}",
                explicit,
                ["explicit contradiction event"],
                "manual_review",
                "high",
                stable_key="explicit-contradiction",
            )
        )
    return signals


def _build_signal(
    signal_type: SignalType,
    summary: str,
    events: list[_Event],
    confidence_points: list[str],
    target_layer: str,
    risk_level: RiskLevel,
    *,
    stable_key: str,
) -> MetaLearningSignal:
    evidence = [
        {
            "session_id": event.session_id,
            "kind": event.kind,
            "summary": event.summary,
        }
        for event in events
    ]
    source_sessions = sorted({event.session_id for event in events})
    recency = max((event.timestamp for event in events if event.timestamp), default=None)
    signal_id = _stable_signal_id(signal_type, stable_key, source_sessions)
    return MetaLearningSignal(
        signal_id=signal_id,
        type=signal_type,
        summary=summary,
        evidence=evidence,
        source_sessions=source_sessions,
        frequency=len(events),
        recency=recency,
        confidence_points=confidence_points,
        recommended_target_layer=target_layer,
        risk_level=risk_level,
    )


def _stable_signal_id(signal_type: SignalType, stable_key: str, source_sessions: list[str]) -> str:
    raw = json.dumps(
        {"type": signal_type, "key": stable_key, "sessions": source_sessions},
        sort_keys=True,
    )
    return f"meta-signal-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _corrections_from_text(text: str) -> list[str]:
    corrections: list[str] = []
    for pattern in CORRECTION_PATTERNS:
        for match in pattern.finditer(text):
            corrections.append(match.group(0).strip())
    return corrections


def _directives_from_text(text: str) -> list[tuple[str, str]]:
    directives: list[tuple[str, str]] = []
    for directive in ("always", "never"):
        pattern = re.compile(rf"\b{directive}\s+(?P<body>[^.!?\n]+)", re.IGNORECASE)
        for match in pattern.finditer(text):
            directives.append((directive, match.group("body").strip()))
    return directives


def _target_layer_for_correction(text: str) -> str:
    lowered = text.lower()
    if "in this repo" in lowered:
        return "project_rule"
    if any(token in lowered for token in ("command", "pnpm", "uv", "git", "cli")):
        return "command_suggestion"
    if any(token in lowered for token in ("skill", "agent", "subagent")):
        return "skill_or_agent_suggestion"
    return "observe_only"


def _risk_for_text(text: str) -> RiskLevel:
    lowered = text.lower()
    if any(token in lowered for token in ("secret", "credential", "deploy", "delete", "destructive")):
        return "high"
    if any(token in lowered for token in ("always", "never", "global", "agent rule")):
        return "medium"
    return "low"


def _recurrence_points(events: list[_Event]) -> list[str]:
    if len(events) <= 1:
        return []
    return [f"frequency={len(events)}", f"source_sessions={len({event.session_id for event in events})}"]


def _group_repeated(events: list[_Event], *, kind: str) -> dict[str, list[_Event]]:
    grouped = _group_by_summary([event for event in events if event.kind == kind])
    return {key: group for key, group in grouped.items() if len(group) > 1}


def _group_by_summary(events: list[_Event]) -> dict[str, list[_Event]]:
    grouped: dict[str, list[_Event]] = defaultdict(list)
    for event in events:
        grouped[_normalize_key(event.summary)].append(event)
    return {key: group for key, group in grouped.items() if group}


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _matches_any(text: str, patterns: Sequence[str]) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in patterns)


def _event_blob(event: _Event) -> str:
    return f"{event.kind} {event.text} {event.metadata}".lower()


def _text_from_mapping(item: Mapping[str, Any]) -> str:
    for key in ("text", "content", "summary", "message"):
        value = item.get(key)
        if isinstance(value, str):
            return value.strip()
    return ""


def _list_of_mappings(raw: Any) -> list[Mapping[str, Any]]:
    return [item for item in raw if isinstance(item, Mapping)] if isinstance(raw, list) else []


def _string_list(raw: Any) -> list[str]:
    return [str(item) for item in raw if isinstance(item, str)] if isinstance(raw, list) else []


def _optional_str(raw: Any) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None
