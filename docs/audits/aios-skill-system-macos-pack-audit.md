# AIOS Skill System macOS Pack Audit

**Phase:** 21, macOS Native App Skill Pack  
**Requirement:** MACS-01  
**Date:** 2026-06-23

## Scope

This audit maps current AIOS skill, instruction, router, TMCP, manifest, validation, provenance, dependency-map, permission-gate, and behavioral-test conventions before adding macOS platform skills.

The Phase 21 macOS pack should be task-routed and intent-specific. It should not become broad always-loaded macOS context.

## Current Skill Surfaces

| Surface | Current Path | Observed Convention |
| --- | --- | --- |
| Project skills | `skills/*/SKILL.md` | Markdown skill folders, sometimes with YAML front matter, use-case text, procedure, output expectations, and reference-file pointers. |
| Skill registry | `config/workflows/skills.json` | Machine-readable skill records with `key`, `purpose`, `allowed_stages`, schemas, invariants, failure conditions, side effects, execution mode, lifecycle state, applicability, and optional `source_path`. |
| Workflow registry | `config/workflows/registry.json` | Stage-based workflow contracts bind skills, validators, artifacts, and execution surfaces. |
| TMCP overlay | `config/tmcp/portable-dev-process/` | Task/module/branch graph with `manifest.json`, `router.md`, `tasks/`, `modules/`, `branches/`, and routing-case tests. |
| TMCP runtime | `services/tmcp_runtime.py` | Compiles task-specific packets, selects tasks/modules/branches/source skills, records traversal fingerprints, source graph version, selected/skipped nodes, token estimates, validation evidence, and receipt rows. |
| Skill harvest | `services/skills_harvest.py` | Generates `skills.tmcp` router, graph, task nodes, modules, branches, provenance maps, behavior atoms, source hashes, shortcuts, and evaluation scaffolds. |
| Behavioral tests | `tests/test_portable_dev_process_tmcp.py`, `tests/test_skills_harvest.py`, `tests/test_tmcp_runtime.py` | Tests validate manifest node references, task coverage, optional branches, graph metadata, behavior atoms, source-skill provenance, and routing behavior. |

## Skill File Conventions

Observed examples:

- `skills/agentize/SKILL.md`
- `skills/divergent-strategy/SKILL.md`
- `skills/make-interfaces-feel-better/SKILL.md`
- `skills/personalized-humanizer/SKILL.md`

Useful conventions to preserve:

- Keep `SKILL.md` small enough to route and orient.
- Put large detail in adjacent reference files when needed.
- Include explicit "when to use" / "do not use" boundaries.
- Define required output shape.
- State local implementation paths and tests when a service backs the skill.
- Treat prompt/skill evidence as support, not authority over the user request.

Gaps to handle lightly for Phase 21:

- Not every local skill has normalized YAML front matter.
- There is no single checked-in manifest format for all `skills/*` folders.
- Dependency maps are strong in TMCP graphs but not uniform in plain skill folders.

Recommendation: do not create a broad new skill framework in Plan 21. Use the existing `SKILL.md` plus TMCP manifest conventions, and add a validation script only when Plan 21 reaches MACS-08.

## TMCP Conventions

`config/tmcp/portable-dev-process/manifest.json` is the strongest current pack pattern.

Required node shapes:

- `nodes.tasks.<task_id>.path`
- `nodes.tasks.<task_id>.triggers`
- `nodes.tasks.<task_id>.requires`
- `nodes.tasks.<task_id>.outputs`
- `nodes.modules.<module_id>`
- `nodes.branches.<branch_id>`
- `edges[]` with `from`, `to`, and `when`
- `install_targets[]`

Router conventions from `config/tmcp/portable-dev-process/router.md`:

- Start by loading the manifest.
- Use read-only default branches unless mutation is explicit.
- Route by IF-style task triggers.
- Consider adjacent tasks only when they add behavior.
- Exit after the smallest behavior-changing node set.
- Record skipped plausible nodes in traversal receipts.

Runtime graph conventions from `services/tmcp_runtime.py` and `services/skills_harvest.py`:

- Node IDs use `@task:<id>`, `@module:<id>`, `@branch:<id>`, and `@source_skill:<id>`.
- Graph schema is `tmcp-graph-v0.1`.
- Nodes may carry `behavior_atoms`, `token_cost`, `redundancy_group`, `risk_if_omitted`, `source_refs`, and `source_tiers`.
- Shortcut use requires active status, current source graph version, unchanged related source material, and behavioral tests.
- Source-specific behavior should be preferred over generic modules when it adds the same behavior with stronger provenance.

## Permission Gates

Existing permission-gate language appears in:

- `config/tmcp/portable-dev-process/modules/tool_safety.md`
- `config/tmcp/portable-dev-process/branches/destructive_action.branch.md`
- `config/tmcp/portable-dev-process/branches/network_required.branch.md`
- `config/tmcp/portable-dev-process/branches/explicit_mutation.branch.md`
- `config/tmcp/portable-dev-process/tasks/dependency_audit.md`

Patterns to preserve:

- Read before mutation.
- Request approval for network, dependency install, remote access, destructive actions, outside-repo writes, and publish/release actions.
- Explain target, blast radius, and recovery path before destructive work.
- Never switch package managers unless explicitly requested.
- Record command failures and verification evidence.

macOS-specific permission gates needed:

- Require explicit approval before signing, notarizing, publishing, changing appcast XML, creating GitHub releases, changing version/build numbers, or touching Sparkle private keys.
- Treat `xcodebuild` verification as allowed read/build verification, but do not mutate signing identities or provisioning settings without approval.
- Do not run release commands in Phase 21 implementation.

## Provenance And Dependency Maps

Current provenance conventions:

- `services/skills_harvest.py` emits source maps, source hashes, source tiers, graph versions, behavior atoms, and source-skill nodes.
- `services/tmcp_runtime.py` records selected nodes, skipped nodes, source graph version, source hashes, traversal fingerprint, validation evidence, and execution outcome.
- `docs/adr/0003-tmcp-decision-graph-traversal.md` records design rationale for graph traversal and shortcut governance.

Current dependency-map conventions:

- TMCP manifests define required modules and optional branches per task.
- TMCP graph edges describe task-to-task transitions.
- Runtime packets include transition traces and selected branches.

macOS pack implication:

- Each macOS task should declare required modules, optional modules/branches, provenance source, freshness/version note, transformation type, and validation expectation.
- Donor material must be transformed and cited, not copied blindly.

## Behavioral Test Conventions

Existing tests validate:

- manifest references point to existing files
- required tasks/modules/branches exist
- routing cases map expected tasks/modules/branches
- optional branches stay optional
- graph JSON contains behavior atoms, token cost, source skill metadata, and source hashes
- runtime packet compilation selects correct task/module/branch nodes

macOS pack tests should follow that shape:

- `tests/test_macos_skill_pack.py` for manifest, task/module/branch path references, broad-trigger checks, provenance fields, permission gates, private-key pattern bans, and release-publish gates.
- Extend `tests/test_tmcp_runtime.py` only if runtime selection needs new cross-namespace behavior.
- Use fixture prompts under the macOS pack, such as `config/tmcp/macos-native-app/tests/routing-cases.json`.

## Recommended Target Paths

| Artifact | Recommended Path |
| --- | --- |
| Donor audit | `docs/audits/macos-app-skills-audit.md` |
| macOS operator docs | `docs/aios/macos-native-app-skill-pack.md` |
| macOS TMCP namespace | `config/tmcp/macos-native-app/` |
| macOS TMCP manifest | `config/tmcp/macos-native-app/manifest.json` |
| macOS TMCP router | `config/tmcp/macos-native-app/router.md` |
| macOS tasks | `config/tmcp/macos-native-app/tasks/*.md` |
| macOS modules | `config/tmcp/macos-native-app/modules/*.md` |
| macOS permission branches | `config/tmcp/macos-native-app/branches/*.branch.md` |
| macOS routing tests | `config/tmcp/macos-native-app/tests/routing-cases.json` |
| macOS skill folders | `skills/macos-project-detection/`, `skills/macos-xcodebuild-verification/`, `skills/macos-release-pipeline/` |
| Skill registry entries | `config/workflows/skills.json` |
| TMCP namespace registry | `config/tmcp/registry.json` |
| Validation tests | `tests/test_macos_skill_pack.py` |
| Validation script, if needed | `scripts/validate-macos-skill-pack.py` |

## Required macOS Node Set

Recommended task nodes:

- `@task:macos_project_detect`
- `@task:xcodebuild_verify`
- `@task:macos_native_pattern`
- `@task:macos_settings_window`
- `@task:sparkle_update`
- `@task:notch_overlay`
- `@task:macos_release_pipeline`

Recommended modules:

- `@module:xcode_environment`
- `@module:scheme_discovery`
- `@module:signing_fallback`
- `@module:error_repair`
- `@module:menu_bar`
- `@module:window_panel`
- `@module:screen_geometry`
- `@module:keyboard_shortcuts`
- `@module:file_picker`
- `@module:pasteboard`
- `@module:drag_drop`
- `@module:navigation_inspector`
- `@module:launch_login`
- `@module:quicklook_workspace`
- `@module:screencapturekit`
- `@module:userdefaults_appstorage`
- `@module:sparkle_appcast_safety`
- `@module:notarization_safety`

Recommended branches:

- `@branch:read_only_detect`
- `@branch:build_verification`
- `@branch:signing_required`
- `@branch:network_required`
- `@branch:release_publish_gate`
- `@branch:secret_material_gate`
- `@branch:destructive_project_change`

## Missing Conventions To Create Lightly

Phase 21 should create small, local conventions for:

- macOS pack manifest provenance fields
- broad-trigger lint for platform skills
- private-key and Sparkle secret pattern checks
- release gate validation
- donor freshness/version notes

Do not generalize these into a repo-wide skill framework unless repeated use outside the macOS pack justifies it.

## Implementation Order Recommendation

1. Plan 21-02 audits donor material and maps adoption/rejection decisions.
2. Plan 21-03 adds project detection and xcodebuild verification skills plus initial TMCP task nodes.
3. Plan 21-04 adds native pattern modules as small task-routed files.
4. Plan 21-05 adds settings, Sparkle, and notch guarded tasks.
5. Plan 21-06 adds release pipeline branches and hard gates.
6. Plan 21-07 wires TMCP namespace registry, manifests, provenance, dependency maps, and node IDs.
7. Plan 21-08 adds validation tests/script.
8. Plan 21-09 writes final docs and report.

## Audit Verdict

AIOS already has enough skill, TMCP, provenance, and behavioral-test conventions to build the macOS pack without broad new framework work. The macOS pack should be a task-routed TMCP namespace with a few thin skill folders and focused validation. Missing conventions should be added as pack-local checks first.
