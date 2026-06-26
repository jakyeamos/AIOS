# Research Domain Writing Boundary Audit

**Date:** 2026-06-26
**Scope:** `research-domain-writing/`
**Decision:** standalone tool; keep out of AIOS core and plan extraction after a small hardening pass.
**Execution outcome:** completed on 2026-06-26. RDW now lives at `/Users/jakyeamos/research-domain-writing`, remote `git@github.com:jakyeamos/research-domain-writing.git`, with `v0.1.0` pushed at commit `ba0f608`. AIOS should consume it through installed skills or thin adapters.

## Summary

`research-domain-writing` is already shaped as a standalone product, not as core AIOS runtime code. It has its own user-facing README, skill entrypoint, slash command installers, domain packs, prompts, examples, local knowledge store, output folders, and future AIOS integration notes. Its own docs explicitly say it is standalone today and deliberately avoids AIOS memory, registry, managed runtime, SQLite storage, and workflow coupling.

The right AIOS boundary is:

- RDW core pipeline, prompts, domain packs, examples, installer, and packet validation live outside AIOS.
- AIOS may keep a thin adapter or skill registration path if AIOS wants to invoke RDW.
- Future AIOS integration should be adapter-based: suggest packets, guard humanizer-only paths, and propose reviewable writebacks without absorbing RDW internals.

## Evidence

- `research-domain-writing/README.md` describes a standalone file-based pipeline: research, grounded copy, QA, then humanizer/blader.
- `research-domain-writing/SKILL.md` is a first-class skill entrypoint with `/rdw` and `/rdw-batch` surfaces.
- `research-domain-writing/install/install.sh` installs Claude commands, Cursor skills, and Codex/agent skill symlinks.
- `research-domain-writing/docs/FUTURE-AIOS-INTEGRATION.md` says AIOS integration is not implemented and warns not to assume AIOS registry/runtime coupling.
- AIOS references outside the subtree are light: no-op instruction scans, skill inventory, truth docs, and skill-family detection.
- There is no nested `.git` repo. `git -C research-domain-writing status` resolves to the parent AIOS repo.
- `research-domain-writing/scripts/validate-packet.py` exists, but without PyYAML installed it only checks file existence.
- `research-domain-writing/outputs/` currently contains only `.gitkeep` placeholders, so there is no local output state blocking extraction.

## Ownership Classification

| Area | Classification | Rationale |
| --- | --- | --- |
| RDW pipeline prompts and orchestrator | `standalone_tool` | Product-specific writing workflow with independent user value. |
| Domain packs and examples | `standalone_tool` | Belong with the RDW product, not AIOS runtime. |
| Knowledge packets and output folders | `standalone_tool` with local-state caveat | File-backed state is part of RDW's product model. |
| Installers and slash command templates | `standalone_tool` | Distribution surface for RDW across agents/editors. |
| Future AIOS hook suggestions | `adapter_inside_aios` later | AIOS should integrate through thin suggestions/writeback adapters only. |

## Boundary Decision

RDW should not remain long-term as an AIOS subtree. It should become its own repo and AIOS should consume it as a skill/tool. This is a stronger extraction candidate than CTS or the agent eval harness because it is already self-contained and has weaker coupling to AIOS internals.

Do not merge RDW into AIOS humanizer, context compiler, or success criteria. The core RDW design depends on separating knowledge generation, domain drafting, QA, and style transformation.

## Pre-Extraction Hardening

Before physical extraction, do a narrow hardening pass:

1. Add repo metadata: `README.md` already exists, but add `RELEASE.md`, `CHANGELOG.md`, and a minimal `.gitignore`.
2. Add dependency policy for the optional YAML validator. Either vendor no dependencies and accept file-existence-only mode, or add a real Python package config with PyYAML as an optional/test dependency.
3. Add focused checks:
   - packet validator succeeds on the basketball sample with PyYAML installed
   - `scripts/new-domain.sh` can scaffold a temp domain
   - install templates contain the expected `__RDW_ROOT__` placeholders
   - no generated outputs are tracked except `.gitkeep`
4. Replace AIOS-specific installer wording with repo-agnostic project install behavior. Current `install.sh` has an AIOS-specific project `.cursor/skills` branch.
5. Decide whether `knowledge/basketball/jalen-brunson-2024-25.yaml` is sample fixture data or user-owned knowledge. If user-owned, move it out of the package before extraction.

## Extraction Plan

Recommended repo name:

`jakyeamos/research-domain-writing`

Initial extraction should preserve the current file-first model:

- prompts
- config
- domain packs
- examples
- install templates
- scripts
- docs
- skill entrypoint

AIOS should retain only:

- a skill reference or symlink/install note
- optional future adapter docs
- ownership map entry pointing to the external repo

## Risks

- RDW is prompt-heavy, so test coverage must focus on contract/shape checks rather than pretending to test copy quality.
- Knowledge packets may mix sample data and personal reusable research. Extraction should avoid accidentally publishing private or low-confidence user knowledge.
- If RDW grows a batch CLI, that CLI should live in the RDW repo, not AIOS.

## Recommendation

Proceed with RDW extraction after the hardening pass above. Do not extract another AIOS-adjacent runtime subsystem before this one unless there is an urgent blocker; RDW is already closer to standalone-tool status than most remaining incubator candidates.
