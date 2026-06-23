from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

CAUSAL_PREDICATES: frozenset[str] = frozenset({"caused_by", "depends_on", "blocks", "supersedes"})
HISTORY_STATUSES: frozenset[str] = frozenset({"superseded", "contradicted", "uncertain"})
VALID_MODES: frozenset[str] = frozenset({"include_history", "current_truth_only"})

RowMapping = Mapping[str, object]


@dataclass(frozen=True)
class _Section:
    heading: str
    lines: tuple[str, ...]
    priority: int
    required: bool = False

    def render(self) -> str:
        return "\n".join((self.heading, *self.lines))


class MemoryCompiler:
    def __init__(
        self,
        *,
        raw_sources: Sequence[RowMapping] = (),
        facts: Sequence[RowMapping] = (),
        relationships: Sequence[RowMapping] = (),
    ) -> None:
        self.raw_sources = {str(row["id"]): dict(row) for row in raw_sources if row.get("id")}
        self.facts = {str(row["id"]): dict(row) for row in facts if row.get("id")}
        self.relationships = {str(row["id"]): dict(row) for row in relationships if row.get("id")}

    def compile(
        self,
        retrieved_ids: dict,
        mode: str = "include_history",
        token_budget: int = 900,
    ) -> str:
        if mode not in VALID_MODES:
            allowed = ", ".join(sorted(VALID_MODES))
            raise ValueError(f"Unsupported memory compile mode '{mode}'. Use: {allowed}.")

        fact_ids = _ids_for(retrieved_ids, "fact_ids", "facts")
        relationship_ids = _ids_for(retrieved_ids, "relationship_ids", "relationships")
        source_ids = _ids_for(retrieved_ids, "source_ids", "sources")

        retrieved_facts = [self.facts[fact_id] for fact_id in fact_ids if fact_id in self.facts]
        causal_chain = self._causal_chain(fact_ids, relationship_ids)
        retrieved_relationships = [
            self.relationships[relationship_id]
            for relationship_id in relationship_ids
            if relationship_id in self.relationships
        ]

        section_builders: list[_Section] = []
        section_builders.extend(self._current_truth_section(retrieved_facts))
        section_builders.extend(self._constraints_section(retrieved_facts, causal_chain))
        if causal_chain:
            section_builders.append(
                _Section(
                    "## Causal / Dependency Chain",
                    tuple(self._format_relationship(row) for row in causal_chain),
                    priority=3,
                )
            )

        if mode == "include_history":
            section_builders.extend(
                self._prior_decisions_section(retrieved_facts, retrieved_relationships)
            )
            section_builders.extend(self._history_section(retrieved_facts))
            section_builders.extend(
                self._open_questions_section(retrieved_facts, retrieved_relationships)
            )

        provenance = self._provenance_section(
            retrieved_facts,
            (*retrieved_relationships, *causal_chain),
            source_ids,
        )
        sections = self._fit_budget(section_builders, provenance, token_budget)
        return "\n\n".join(
            ("# Relevant Memory Briefing", *(section.render() for section in sections))
        )

    def _current_truth_section(self, facts: Sequence[RowMapping]) -> list[_Section]:
        lines = [
            _format_fact(row)
            for row in facts
            if row.get("validity_status", "active") == "active"
            and not _is_constraint_fact(row)
            and not _is_prior_decision_fact(row)
            and not _is_open_question_fact(row)
        ]
        return [_Section("## Current Truth", tuple(lines), priority=1)] if lines else []

    def _constraints_section(
        self, facts: Sequence[RowMapping], relationships: Sequence[RowMapping]
    ) -> list[_Section]:
        lines = [_format_fact(row) for row in facts if _is_constraint_fact(row)]
        lines.extend(
            self._format_relationship(row)
            for row in relationships
            if row.get("predicate") == "has_constraint"
        )
        return [_Section("## Constraints", tuple(lines), priority=2)] if lines else []

    def _prior_decisions_section(
        self, facts: Sequence[RowMapping], relationships: Sequence[RowMapping]
    ) -> list[_Section]:
        lines = [_format_fact(row) for row in facts if _is_prior_decision_fact(row)]
        lines.extend(
            self._format_relationship(row)
            for row in relationships
            if row.get("predicate") == "decided_in"
        )
        return [_Section("## Relevant Prior Decisions", tuple(lines), priority=4)] if lines else []

    def _history_section(self, facts: Sequence[RowMapping]) -> list[_Section]:
        lines = [
            f"- {row.get('validity_status')}: {_text(row.get('fact_text'))}"
            for row in facts
            if row.get("validity_status") in HISTORY_STATUSES
        ]
        return (
            [_Section("## Contradictions or Stale Information", tuple(lines), priority=5)]
            if lines
            else []
        )

    def _open_questions_section(
        self, facts: Sequence[RowMapping], relationships: Sequence[RowMapping]
    ) -> list[_Section]:
        lines = [_format_fact(row) for row in facts if _is_open_question_fact(row)]
        lines.extend(
            self._format_relationship(row)
            for row in relationships
            if row.get("predicate") == "has_open_question"
        )
        return [_Section("## Open Questions", tuple(lines), priority=6)] if lines else []

    def _causal_chain(
        self, fact_ids: Sequence[str], relationship_ids: Sequence[str]
    ) -> tuple[RowMapping, ...]:
        included: list[RowMapping] = []
        seen_relationships: set[str] = set()
        frontier = set(fact_ids)
        remaining_depth = 3
        for relationship_id in relationship_ids:
            row = self.relationships.get(relationship_id)
            if row is None or row.get("predicate") not in CAUSAL_PREDICATES:
                continue
            included.append(row)
            seen_relationships.add(relationship_id)
            frontier.add(_text(row.get("subject_id")))
            frontier.add(_text(row.get("object_id")))
            remaining_depth = 2

        for _depth in range(remaining_depth):
            next_frontier: set[str] = set()
            for relationship_id, row in self.relationships.items():
                if (
                    relationship_id in seen_relationships
                    or row.get("predicate") not in CAUSAL_PREDICATES
                ):
                    continue
                subject_id = _text(row.get("subject_id"))
                object_id = _text(row.get("object_id"))
                if subject_id not in frontier and object_id not in frontier:
                    continue
                included.append(row)
                seen_relationships.add(relationship_id)
                next_frontier.update((subject_id, object_id))
            if not next_frontier:
                break
            frontier = next_frontier
        return tuple(included)

    def _provenance_section(
        self,
        facts: Sequence[RowMapping],
        relationships: Sequence[RowMapping],
        explicit_source_ids: Sequence[str],
    ) -> _Section:
        source_ids = list(explicit_source_ids)
        source_ids.extend(_text(row.get("source_id")) for row in facts if row.get("source_id"))
        source_ids.extend(
            _text(row.get("source_id")) for row in relationships if row.get("source_id")
        )

        lines: list[str] = []
        seen: set[str] = set()
        for source_id in source_ids:
            if source_id in seen:
                continue
            seen.add(source_id)
            source = self.raw_sources.get(source_id)
            if source is None:
                continue
            source_type = _text(source.get("source_type")) or "unknown"
            source_path = _text(source.get("source_path")) or "(no path)"
            lines.append(f"- {source_type}: {source_path}")

        if not lines:
            lines.append("- No source rows supplied.")
        return _Section("## Sources / Provenance", tuple(lines), priority=7, required=True)

    def _format_relationship(self, row: RowMapping) -> str:
        subject = self.facts.get(_text(row.get("subject_id")), {})
        object_row = self.facts.get(_text(row.get("object_id")), {})
        subject_text = _text(subject.get("fact_text")) or _text(row.get("subject_id"))
        object_text = _text(object_row.get("fact_text")) or _text(row.get("object_id"))
        predicate = _text(row.get("predicate"))
        return f"- {subject_text} -- {predicate} -> {object_text}"

    def _fit_budget(
        self, optional_sections: Sequence[_Section], provenance: _Section, token_budget: int
    ) -> tuple[_Section, ...]:
        sections = list(optional_sections)
        if token_budget <= 0:
            return (provenance,)

        while (
            sections and _estimated_tokens(_render_packet((*sections, provenance))) > token_budget
        ):
            lowest_priority = max(section.priority for section in sections)
            for index in range(len(sections) - 1, -1, -1):
                if sections[index].priority == lowest_priority:
                    del sections[index]
                    break
        return (*sections, provenance)


def _ids_for(retrieved_ids: Mapping[object, object], *keys: str) -> tuple[str, ...]:
    values: list[str] = []
    for key in keys:
        raw_value = retrieved_ids.get(key)
        if raw_value is None:
            continue
        if isinstance(raw_value, str):
            values.append(raw_value)
            continue
        if isinstance(raw_value, Sequence):
            values.extend(str(value) for value in raw_value)
    return tuple(dict.fromkeys(value for value in values if value))


def _is_constraint_fact(row: RowMapping) -> bool:
    return (
        row.get("predicate") == "has_constraint" or _text(row.get("entity")).lower() == "constraint"
    )


def _is_prior_decision_fact(row: RowMapping) -> bool:
    return row.get("predicate") == "decided_in" or _text(row.get("entity")).lower() == "decision"


def _is_open_question_fact(row: RowMapping) -> bool:
    fact_text = _text(row.get("fact_text"))
    return (
        row.get("predicate") == "has_open_question"
        or _text(row.get("entity")).lower() == "open_question"
        or fact_text.endswith("?")
    )


def _format_fact(row: RowMapping) -> str:
    return f"- {_text(row.get('fact_text'))}"


def _text(value: object) -> str:
    return value if isinstance(value, str) else "" if value is None else str(value)


def _render_packet(sections: Sequence[_Section]) -> str:
    return "\n\n".join(("# Relevant Memory Briefing", *(section.render() for section in sections)))


def _estimated_tokens(text: str) -> int:
    return max(1, len(text) // 4)
