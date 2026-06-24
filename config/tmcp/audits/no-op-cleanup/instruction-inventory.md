# Instruction Inventory

Date: 2026-06-24

Inventory command:

```bash
node tools/no-op-instruction-scan.mjs --json
```

Result: 96 active editable instruction files scanned.

## Root And Agent Rules

- `AGENTS.md`
- `config/agent-rules.md`

## TMCP

- `config/tmcp/behavior-atoms.json`
- `config/tmcp/canonical-graph.json`
- `config/tmcp/golden-prompts.json`
- `config/tmcp/macos-skills-router.json`
- `config/tmcp/no-op-scan-allowlist.json`
- `config/tmcp/portable-dev-process/README.md`
- `config/tmcp/portable-dev-process/branches/destructive_action.branch.md`
- `config/tmcp/portable-dev-process/branches/explicit_mutation.branch.md`
- `config/tmcp/portable-dev-process/branches/network_required.branch.md`
- `config/tmcp/portable-dev-process/branches/read_only_default.branch.md`
- `config/tmcp/portable-dev-process/branches/tenure_visual_identity.branch.md`
- `config/tmcp/portable-dev-process/manifest.json`
- `config/tmcp/portable-dev-process/modules/ai_surface_polish.md`
- `config/tmcp/portable-dev-process/modules/ci_triage.md`
- `config/tmcp/portable-dev-process/modules/command_discovery.md`
- `config/tmcp/portable-dev-process/modules/data_realism_polish.md`
- `config/tmcp/portable-dev-process/modules/dependency_policy.md`
- `config/tmcp/portable-dev-process/modules/diff_review.md`
- `config/tmcp/portable-dev-process/modules/doc_update.md`
- `config/tmcp/portable-dev-process/modules/enterprise_saas_visual_polish.md`
- `config/tmcp/portable-dev-process/modules/frontend_runtime.md`
- `config/tmcp/portable-dev-process/modules/git_hygiene.md`
- `config/tmcp/portable-dev-process/modules/hook_guidance.md`
- `config/tmcp/portable-dev-process/modules/instruction_hygiene.md`
- `config/tmcp/portable-dev-process/modules/make_interfaces_feel_better.md`
- `config/tmcp/portable-dev-process/modules/quality_gate.md`
- `config/tmcp/portable-dev-process/modules/reproduce_first.md`
- `config/tmcp/portable-dev-process/modules/test_authoring.md`
- `config/tmcp/portable-dev-process/modules/tool_safety.md`
- `config/tmcp/portable-dev-process/modules/visual_polish_system.md`
- `config/tmcp/portable-dev-process/router.md`
- `config/tmcp/portable-dev-process/tasks/add_tests.md`
- `config/tmcp/portable-dev-process/tasks/ci_triage.md`
- `config/tmcp/portable-dev-process/tasks/debug_failure.md`
- `config/tmcp/portable-dev-process/tasks/dependency_audit.md`
- `config/tmcp/portable-dev-process/tasks/docs_update.md`
- `config/tmcp/portable-dev-process/tasks/frontend_verify.md`
- `config/tmcp/portable-dev-process/tasks/git_hygiene.md`
- `config/tmcp/portable-dev-process/tasks/instruction_hygiene.md`
- `config/tmcp/portable-dev-process/tasks/planning_review.md`
- `config/tmcp/portable-dev-process/tasks/quality_check.md`
- `config/tmcp/portable-dev-process/tasks/repo_detect.md`
- `config/tmcp/portable-dev-process/tasks/review_diff.md`
- `config/tmcp/portable-dev-process/tasks/visual_polish.md`
- `config/tmcp/portable-dev-process/tests/routing-cases.json`
- `config/tmcp/registry.json`

## Workflow Registries

- `config/workflows/registry.json`
- `config/workflows/skills.json`

## Prompt Library

- `prompts/README.md`
- `prompts/behavioral_spec_verification.md`
- `prompts/coding_debug.md`
- `prompts/content_writing.md`
- `prompts/evals/coding_debug/cases.md`
- `prompts/evals/content_writing/cases.md`
- `prompts/evals/reasoning/cases.md`
- `prompts/evals/research/cases.md`
- `prompts/evals/summarization/cases.md`
- `prompts/reasoning.md`
- `prompts/registry.json`
- `prompts/research.md`
- `prompts/summarization.md`

## Project Skills

- `skills/agentize/SKILL.md`
- `skills/divergent-strategy/SKILL.md`
- `skills/divergent-strategy/references/candidates.md`
- `skills/divergent-strategy/references/entropy.md`
- `skills/divergent-strategy/references/judges.md`
- `skills/divergent-strategy/references/memory-writebacks.md`
- `skills/divergent-strategy/references/promotion-gates.md`
- `skills/macos/build-verify/SKILL.md`
- `skills/macos/native-patterns-router/SKILL.md`
- `skills/macos/notch-overlay/SKILL.md`
- `skills/macos/project-detection/SKILL.md`
- `skills/macos/release-pipeline/SKILL.md`
- `skills/macos/settings-window/SKILL.md`
- `skills/macos/sparkle-auto-update/SKILL.md`
- `skills/make-interfaces-feel-better/SKILL.md`
- `skills/operating-language/SKILL.md`
- `skills/operating-language/agents/openai.yaml`
- `skills/personalized-humanizer/SKILL.md`

## RDW And Cursor Skill Surfaces

- `.cursor/skills/rdw-batch/SKILL.md`
- `.cursor/skills/rdw/SKILL.md`
- `research-domain-writing/SKILL.md`
- `research-domain-writing/install/codex-skills/research-domain-writing/SKILL.md`
- `research-domain-writing/install/cursor-skills/rdw-batch/SKILL.md`
- `research-domain-writing/install/cursor-skills/rdw/SKILL.md`
- `research-domain-writing/prompts/batch-runner.md`
- `research-domain-writing/prompts/domain-copywriter.md`
- `research-domain-writing/prompts/domain-qa.md`
- `research-domain-writing/prompts/domain-router.md`
- `research-domain-writing/prompts/humanizer-blader.md`
- `research-domain-writing/prompts/knowledge-packet-builder.md`
- `research-domain-writing/prompts/pipeline-orchestrator.md`
- `research-domain-writing/prompts/research-planner.md`
- `research-domain-writing/prompts/researcher.md`
