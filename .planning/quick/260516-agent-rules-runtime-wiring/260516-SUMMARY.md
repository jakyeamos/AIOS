# Quick Task 260516: Agent Rules Runtime Wiring - Summary

## Result

`config/agent-rules.md` now feeds the actual AIOS runtime surfaces:

- `bin/hook-session-start.py` injects parsed agent rules into the session context packet.
- `tools/context-compile.mjs` selects `config/agent-rules.md` as synthetic immutable global context and includes it in receipts.
- `services/workflow_orchestration.py` loads agent rules into workflow state, normalized prompts, and report artifacts.
- `bin/sync-installed-skills.py` writes installed skill `source_path` and `installed_name` metadata, and workflow execution reports that metadata per skill.

## Verification

- `uv run pytest -q tests/test_agent_rules_runtime.py tests/test_workflow_orchestration.py`
- `pnpm test:context`
- Live session-start invocation emitted the `AIOS agent rules` block in the injected context.
- Live context compile selected `config/agent-rules.md` as `config.agent-rules`.
