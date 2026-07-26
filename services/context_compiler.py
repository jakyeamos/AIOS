from __future__ import annotations

from collections.abc import Mapping, Sequence

from services.memory_compiler import MemoryCompiler

RowMapping = Mapping[str, object]

HISTORY_STATUSES: frozenset[str] = frozenset({"superseded", "contradicted", "archived"})


class ContextCompiler:
    def __init__(
        self,
        *,
        system_instructions: str = "You are operating inside AIOS.",
        aios_operating_rules: Sequence[str] = (),
        user_preferences: Sequence[str] = (),
        project_memory_summaries: Mapping[str, str] | None = None,
        project_context_facts: Sequence[RowMapping] = (),
        raw_sources: Sequence[RowMapping] = (),
        retrieved_facts: Sequence[RowMapping] = (),
        retrieved_relationships: Sequence[RowMapping] = (),
        scratchpad_results: Sequence[str] = (),
    ) -> None:
        self.system_instructions = system_instructions
        self.aios_operating_rules = tuple(aios_operating_rules)
        self.user_preferences = tuple(user_preferences)
        self.project_memory_summaries = dict(project_memory_summaries or {})
        self.project_context_facts = tuple(dict(row) for row in project_context_facts)
        self.raw_sources = tuple(dict(row) for row in raw_sources)
        self.retrieved_facts = tuple(dict(row) for row in retrieved_facts)
        self.retrieved_relationships = tuple(dict(row) for row in retrieved_relationships)
        self.scratchpad_results = tuple(scratchpad_results)

    def compile(
        self,
        task: str,
        project_id: str,
        budget: int,
        *,
        staleness_filter: bool = True,
        adapter: object | None = None,
    ) -> list[dict[str, str]]:
        del adapter

        project_context_facts = self._project_context_facts(project_id, staleness_filter)
        context_texts = {_fact_text(row) for row in project_context_facts if _fact_text(row)}
        dynamic_facts = self._dynamic_facts(project_id, staleness_filter, context_texts)
        dynamic_relationships = self._dynamic_relationships(project_id)

        stable_sections = [
            _section("system", "System / Developer Instructions", self.system_instructions),
            _section("developer", "AIOS Operating Rules", _bullet_list(self.aios_operating_rules)),
            _section("developer", "User Preferences", _bullet_list(self.user_preferences)),
            _section(
                "developer",
                "Project Memory Summary",
                self.project_memory_summaries.get(
                    project_id, "No project memory summary supplied."
                ),
            ),
            _section("developer", "Project Context Packet", _fact_list(project_context_facts)),
        ]
        dynamic_sections = [
            _section(
                "user",
                "Task-Specific Retrieved Memory",
                self._dynamic_memory(dynamic_facts, dynamic_relationships),
            ),
            _section("user", "Current User Request / Task Description", task),
        ]
        if self.scratchpad_results:
            dynamic_sections.append(
                _section("user", "Scratchpad / Tool Results", _bullet_list(self.scratchpad_results))
            )

        sections = self._fit_budget(stable_sections, dynamic_sections, budget)
        return [{"role": section["role"], "content": section["content"]} for section in sections]

    def _project_context_facts(
        self, project_id: str, staleness_filter: bool
    ) -> tuple[RowMapping, ...]:
        rows = [
            row
            for row in self.project_context_facts
            if _matches_project(row, project_id) and _passes_staleness(row, staleness_filter)
        ]
        return tuple(sorted(rows, key=lambda row: (_fact_text(row), _text(row.get("id")))))

    def _dynamic_facts(
        self, project_id: str, staleness_filter: bool, context_texts: set[str]
    ) -> tuple[RowMapping, ...]:
        rows = [
            row
            for row in self.retrieved_facts
            if _matches_project(row, project_id)
            and _passes_staleness(row, staleness_filter)
            and _fact_text(row) not in context_texts
        ]
        return tuple(sorted(rows, key=lambda row: (_fact_text(row), _text(row.get("id")))))

    def _dynamic_relationships(self, project_id: str) -> tuple[RowMapping, ...]:
        rows = [row for row in self.retrieved_relationships if _matches_project(row, project_id)]
        return tuple(sorted(rows, key=lambda row: _text(row.get("id"))))

    def _dynamic_memory(
        self, facts: Sequence[RowMapping], relationships: Sequence[RowMapping]
    ) -> str:
        compiler = MemoryCompiler(
            raw_sources=self.raw_sources,
            facts=facts,
            relationships=relationships,
        )
        return compiler.compile(
            {
                "fact_ids": [_text(row.get("id")) for row in facts],
                "relationship_ids": [_text(row.get("id")) for row in relationships],
            },
            mode="include_history",
            token_budget=600,
        )

    def _fit_budget(
        self,
        stable_sections: Sequence[dict[str, str]],
        dynamic_sections: Sequence[dict[str, str]],
        budget: int,
    ) -> list[dict[str, str]]:
        sections = [dict(section) for section in (*stable_sections, *dynamic_sections)]
        if budget <= 0:
            return sections[:3]

        dynamic_indexes = list(range(len(stable_sections), len(sections)))
        for index in dynamic_indexes:
            if _estimated_tokens(_render_sections(sections)) <= budget:
                break
            sections[index]["content"] = _compress_content(
                sections[index]["content"], minimum_lines=1
            )

        if _estimated_tokens(_render_sections(sections)) > budget:
            truth_index = 4
            sections[truth_index]["content"] = _compress_content(
                sections[truth_index]["content"], minimum_lines=1
            )

        if _estimated_tokens(_render_sections(sections)) > budget:
            summary_index = 3
            sections[summary_index]["content"] = _compress_content(
                sections[summary_index]["content"], minimum_lines=1
            )

        return sections


def _section(role: str, title: str, body: str) -> dict[str, str]:
    content = body.strip() or "No context supplied."
    return {"role": role, "content": f"## {title}\n{content}"}


def _bullet_list(items: Sequence[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "No context supplied."


def _fact_list(facts: Sequence[RowMapping]) -> str:
    lines = [f"- {_fact_text(row)}" for row in facts if _fact_text(row)]
    return "\n".join(lines) if lines else "No project context facts supplied."


def _matches_project(row: RowMapping, project_id: str) -> bool:
    scope = row.get("project_scope") or row.get("project_id")
    return scope is None or scope == project_id


def _passes_staleness(row: RowMapping, staleness_filter: bool) -> bool:
    return not staleness_filter or row.get("validity_status") not in HISTORY_STATUSES


def _fact_text(row: RowMapping) -> str:
    return _text(row.get("fact_text"))


def _text(value: object) -> str:
    return value if isinstance(value, str) else "" if value is None else str(value)


def _render_sections(sections: Sequence[Mapping[str, str]]) -> str:
    return "\n\n".join(section["content"] for section in sections)


def _estimated_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _compress_content(content: str, *, minimum_lines: int) -> str:
    lines = [line for line in content.splitlines() if line.strip()]
    if len(lines) <= minimum_lines:
        return content
    kept = lines[:minimum_lines]
    kept.append("- Additional lower-priority context omitted for token budget.")
    return "\n".join(kept)
