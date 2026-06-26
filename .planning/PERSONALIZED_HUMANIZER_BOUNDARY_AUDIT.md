# Personalized Humanizer Boundary Audit

**Date:** 2026-06-26
**Scope:** `services/personalized_humanizer.py`, `config/personalized-humanizer/`, `skills/personalized-humanizer/`, workflow registry bindings, SQLite tables, and tests.
**Decision:** keep inside AIOS for now; treat as an AIOS memory/persona projection with a possible future portable contract split.

## Summary

The personalized humanizer is not ready for a Research Domain Writing style extraction. RDW was already a standalone file-based product with its own prompts, domain packs, installers, examples, and weak AIOS runtime coupling. The personalized humanizer is different: it is wired into AIOS workflow orchestration, local profile governance, SQLite-backed run/feedback/profile-update storage, workflow learning behavior, and personalized memory/privacy rules.

The right boundary is:

- AIOS continues to own the personalized humanizer runtime, profile lifecycle, workflow stages, local storage, and privacy guardrails.
- Do not move the current profile, skill, workflow stages, or SQLite behavior into a separate repo yet.
- If reuse pressure appears, extract only a small contract package first: voice-profile schema, retrieval-policy schema, voice-packet shape, scorecard dimensions, and eval-result shape.
- Keep generic humanizer cleanup separate from personalized voice adaptation; the current `pipeline_position` contract is the right ownership split.

## Evidence

- `docs/architecture/personalized-humanizer.md` explicitly describes the feature as an AIOS skill for the local user's approved writing voice.
- `services/personalized_humanizer.py` imports AIOS-rooted config paths and owns deterministic primitives plus SQLite persistence helpers.
- `schema.sql` defines durable `personalized_humanizer_*` tables for runs, feedback, profile updates, and eval results.
- `config/workflows/registry.json` registers `personalized-humanizer` as an AIOS workflow with staged parse, context, transform, validate, and finalize behavior.
- `config/workflows/skills.json` defines AIOS skill contracts for classifier, voice retriever, packet builder, transformer, quality checker, and feedback collector.
- `services/workflow_orchestration.py` directly imports and executes personalized humanizer service functions.
- `tests/test_personalized_humanizer.py` covers workflow registry binding and workflow execution, not just standalone library behavior.
- `config/personalized-humanizer/profile.json` is a personal/local profile with privacy policy, provenance, and user-specific style constraints.

## Ownership Map

| Surface | Classification | Rationale |
| --- | --- | --- |
| Rewrite/classification runtime | `core_aios` for now | It is executed through AIOS workflow orchestration and local policy. |
| Profile and retrieval policy files | `core_aios` local memory/persona projection | They are personal, privacy-sensitive, and tied to local review rules. |
| SQLite run/feedback/profile-update tables | `core_aios` | They are part of AIOS memory, evidence, and governed writeback behavior. |
| Skill packet | `core_aios` asset, possible external adapter later | The current skill points at AIOS paths and workflow semantics. |
| Voice profile/scorecard/eval schemas | `contract_package` candidate | These could be made portable without moving runtime or personal data. |
| Generic humanizer cleanup | separate external skill/tool | The personalized humanizer should remain a voice-specific second pass when needed. |

## Why Not Extract Now

1. The runtime is not standalone. It imports AIOS config paths and is called by AIOS workflow orchestration.
2. The state model is AIOS-owned. Runs, feedback, candidate profile updates, and eval results belong to local AIOS memory/governance.
3. The profile is personal data. Extracting it into a general repo would risk mixing reusable code with private preferences and provenance.
4. The workflow value is AIOS-native. Its main value is not a generic rewrite library; it is governed local voice adaptation with feedback-gated learning.
5. The current tests prove AIOS integration. A standalone extraction would need new fixtures that prove behavior without AIOS registry, schema, or local paths.

## Narrow Future Extraction Candidate

If this subsystem needs reuse outside AIOS, extract a contract package before extracting a runtime:

- `VoiceMode`
- voice profile schema
- retrieval policy schema
- `CorpusExample`
- `VoicePacket`
- scorecard dimensions
- eval suite/result schema
- privacy/provenance invariants

That package should have fixtures with synthetic profiles and no private user examples. AIOS would continue to own:

- real local profile data
- SQLite persistence
- feedback lifecycle
- workflow registry/stage execution
- local skill distribution
- memory writeback/promotion rules

## Pre-Extraction Requirements

Before any code extraction is justified:

1. Create synthetic profile fixtures that prove the contract without personal data.
2. Separate pure schema/validation from AIOS workflow and SQLite code.
3. Add a migration plan for profile versioning that does not expose local-user rules.
4. Prove a second consumer outside AIOS needs the contract.
5. Decide whether the generic humanizer remains a separate skill dependency or becomes an adapter input.

## Recommendation

Do not extract personalized humanizer as a standalone repo now. Keep it inside AIOS as a candidate workflow and local memory/persona projection. The next useful work is contract isolation, not repo extraction: define a portable voice-profile/voice-packet/scorecard contract while leaving runtime, personal config, and persistence in AIOS.
