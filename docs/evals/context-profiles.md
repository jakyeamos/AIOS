# AIOS Context Profiles

Date: 2026-06-02
Status: Phase 1 Agent Eval Foundation

## Rule

Every major-task eval must declare exactly one context profile. A richer-context win over a poorer-context run proves lift from that richer context, not portable superiority. In particular, a `jakye_second_brain_full` win over `peer_repo_only` does not prove AIOS is better; it proves the second brain adds lift.

## Profiles

### jakye_second_brain_full

- Definition: Full local AIOS context, including repo files, project truth, planning state, local SQLite state, linked project memory, and relevant private second-brain knowledge.
- Includes: `PROJECT.md`, planning artifacts, compiled packets, standards, local AIOS database state, vault-derived context when relevant, prior run memory, and writeback history.
- Excludes: Secrets, unrelated personal content, and private material not relevant to the task.
- Use when: Measuring personalized local AIOS productivity and second-brain lift.
- Cannot prove: Portable benchmark quality, peer reproducibility, or clean-room performance.

### jakye_second_brain_limited

- Definition: Local AIOS context with selected second-brain material included by explicit task relevance.
- Includes: Repo files, project truth, planning state, standards, selected memory packets, and selected vault or DB-derived references.
- Excludes: Broad private corpus search, unrelated local history, secrets, and personal writing corpus.
- Use when: A task needs some local memory but should avoid broad private-context dependence.
- Cannot prove: Full clean-room portability or performance without local project memory.

### jakye_repo_only

- Definition: Local repo context without second-brain memory or private vault/database context.
- Includes: Checked-in repo files, checked-in docs, checked-in tests, and local commands required by the repo.
- Excludes: Private vault notes, local AIOS DB history, imported conversations, personal corpus data, and cross-project memory.
- Use when: Measuring what the checked-in repo alone supports for Jakye's environment.
- Cannot prove: Peer reproducibility unless environment assumptions and local-only files are also portable.

### peer_repo_only

- Definition: A peer or external agent uses only the repository and ordinary public toolchain context.
- Includes: Checked-in source, docs, tests, configs, and explicitly provided task prompt.
- Excludes: Jakye's private second brain, AIOS local DB, local session history, vault notes, and personal conventions not checked into the repo.
- Use when: Estimating whether another agent can complete the same task from the repo alone.
- Cannot prove: Value of AIOS second-brain context or personalized workflow lift.

### peer_portable_context_packet

- Definition: A peer or external agent receives the repo plus a curated portable context packet.
- Includes: Repo files, selected docs, framework conventions, test commands, success criteria references, known constraints, and task-specific context explicitly listed in the packet.
- Excludes: Personal notes, private project history, unrelated second-brain content, secrets, personal writing corpus, and implicit local DB knowledge.
- Use when: Measuring whether AIOS can package enough context for a non-local agent.
- Cannot prove: Performance with full private memory or without any curated context.

### external_clean_room

- Definition: A clean-room run with only public/repo-available context and no personalized local assumptions.
- Includes: Public repo files, public docs, standard package metadata, public benchmark task statement, and commands available from the clean environment.
- Excludes: Local AIOS database, vault, private corpus, local-only environment hacks, hidden context, and personal operating conventions not in the repo.
- Use when: Preparing external benchmark claims or open-source reproducibility checks.
- Cannot prove: Personalized productivity, second-brain lift, or private workflow value.

## Comparison Semantics

- `jakye_second_brain_full` vs `jakye_repo_only` measures Second Brain Lift.
- `jakye_second_brain_full` vs `peer_portable_context_packet` measures Portability Gap.
- `peer_portable_context_packet` vs `peer_repo_only` measures portable packet lift.
- `external_clean_room` is the only profile suitable for broad external benchmark claims.

Always label results as personalized/local when they use `jakye_second_brain_full` or `jakye_second_brain_limited`.
