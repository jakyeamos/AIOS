# Linked Repo Strict Release Readiness

Date: 2026-06-24
Owner: AIOS
Phase: 23

## Purpose

This contract defines what it means for an active linked repository to be AIOS adoption-ready under strict release standards.

Strict readiness is class-based. A production web app, developer package, research repo, and vault/container repo should not fake the same commands. Each repo must prove the smallest real gate set that matches what it is.

## Command Ownership

Repo-local `.aios-quality-gate.json` files are declarations only.

Allowed repo-local content:

- project id
- declared gate ids
- optional contract metadata

Executable commands must remain AIOS-owned:

- `config/quality-gates.json`
- `config/quality-pipeline.json`
- architecture-enforcement config

This keeps portable hooks from executing arbitrary repo-local shell from untrusted config.

## Universal Readiness Rules

A repo is adoption-ready only when all are true:

- It has a valid `.aios-quality-gate.json`.
- It has no `floor_only` or `pre_cr_only` maturity marker.
- It has a project truth file or agent instruction file that lets AIOS route and evaluate work consistently.
- It has class-appropriate install, lint/static, test, build/package or validation, architecture or pre-cr, secret/dependency security, and CI gates.
- AIOS records fresh passing quality-pipeline evidence for every required class gate.
- `prove-project-health --all-inventory` records an active-inventory standards-health snapshot without missing-source or inactive-row contamination.
- Remote CI passes on the default branch, or AIOS truth records an explicit non-remote exception.
- Remaining dirty tree state is limited to known in-progress work and is recorded separately from adoption readiness.

Weak maturity markers are blockers:

- `floor_only`: a floor check exists, but it is not a mature quality standard.
- `pre_cr_only`: changed-line readiness exists, but no project-specific gate proves the repo.

## Non-Remote CI Exception

Remote CI is required unless remote CI is inappropriate for the repo class.

An exception must be recorded in AIOS truth with:

| Field | Meaning |
| --- | --- |
| owner | Person or agent accountable for the exception |
| reason | Why remote CI is not appropriate |
| review_date | Date when the exception must be re-evaluated |
| local_proof_command | Exact local command replacing remote CI proof |
| replacement_path | Path to the future CI or delegated proof mechanism |

Repos without remote CI and without this exception are not adoption-ready.

## Class Standards

### Platform/control-plane

Applies to: `AIOS`

Required gates:

- install
- lint
- typecheck
- test
- build
- architecture
- pre-cr
- project truth
- secret scan
- dependency security
- CI
- pre-PR readiness
- thermo-nuclear simplification

Additional proof:

- focused control-plane regression tests after registry/schema changes
- context validation
- copied-DB and live-DB standards-health proof when inventory logic changes

### Production/public web app

Applies to: `soundscape-app`, `amos-saas`, `portfolio`, `remodelvision`, `dispatches-from-cyberspace`, `Bballedu`, `tm`

Required gates:

- frozen install
- lint
- typecheck when TypeScript is present
- tests
- production build
- architecture or equivalent app boundary check
- pre-cr changed-line readiness
- project truth or agent instructions
- secret scan
- environment validation
- dependency security
- remote CI or explicit non-remote exception
- smoke or e2e evidence appropriate to the app

Additional proof:

- public web apps should record SEO/Lighthouse or equivalent deploy-surface validation when applicable
- database-backed apps should record migration/restore or seeded smoke evidence when applicable

### Developer tool/package

Applies to: `Terrace`, `pre-cr-suite-lsp`, `eslint-plugin-anti-slop`, `video-pipeline`, `agent-router`

Required gates:

- install
- lint/static analysis
- typecheck when applicable
- tests
- package/build or CLI/consumer smoke
- architecture or package boundary check
- pre-cr changed-line readiness
- project truth or agent instructions
- secret scan
- dependency security
- remote CI or explicit non-remote exception

Additional proof:

- packages should prove their published or consumed surface, not only internal unit tests
- CLIs should prove help or smoke execution for the primary entry point

### Python/data/research/course

Applies to: `LIS`, `R-Project`, `Dsci-proj`, `Fantasy`, `manga-sync`, `career-ops`, `claude-improvement-lab`, `csds391-s26-6`

Required gates:

- install or environment bootstrap when dependencies exist
- lint/static validation when the repo has code
- test or executable smoke when tests exist
- class-specific validation for notebooks, datasets, scripts, assignments, or reports
- architecture or structure validation appropriate to repo shape
- pre-cr changed-line readiness
- project truth or agent instructions
- secret scan
- dependency security when dependencies exist
- remote CI or explicit non-remote exception

Additional proof:

- course repos can use assignment structure validation instead of app build gates
- data repos can use schema/sample/manifest validation instead of fake unit tests
- R repos can use `Rscript` validation or package checks where applicable

### Content/vault/container

Applies to: `Vaults`, `BBDSE`

Required gates:

- aggregate or delegated validation
- architecture or structure validation
- pre-cr changed-line readiness
- project truth or agent instructions
- secret scan
- CI or explicit non-remote exception

Additional proof:

- container repos must validate their child projects or declare which child repo owns each delegated gate
- BBDSE's current `git diff --check` style floor remains non-mature until replaced by aggregate or delegated subproject gates
- vault/content repos should validate links, protected paths, and secret-free content rather than pretending to be applications

## Evidence Rules

Before a repo can remove `floor_only` or `pre_cr_only`, AIOS must record:

- the replacement gate ids
- the AIOS-owned commands
- a fresh local pass for each replacement command
- standards-health proof from active inventory
- CI/default-branch pass or non-remote exception
- any remaining dirty-tree note

Evidence belongs in AIOS, not in optimistic prose.

## Config Mapping

`config/quality-pipeline.json` now carries:

- `standard.classes`
- `standard.non_remote_ci_exception_schema`
- `standard.adoption_readiness_rule`
- `repo_class` metadata for every active Phase 23 repo

Later Phase 23 plans must fill real commands and evidence for the class gates. Empty class metadata is not readiness.
