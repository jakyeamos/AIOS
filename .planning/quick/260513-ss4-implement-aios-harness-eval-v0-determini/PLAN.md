# Implement AIOS Harness Eval V0

## Goal
Add a deterministic, fixture-backed AIOS harness evaluation contract that scores control-plane quality without live model calls.

## Files
- Create `services/harness_eval.py`
- Create `tests/test_harness_eval.py`
- Create `docs/evals/aios-harness-eval-v0.md`
- Create `docs/aios/harness-eval/config.json`
- Create `tests/fixtures/harness-eval/**`
- Modify `services/aios_cli.py`
- Modify `PROJECT.md` in a second truth-file commit

## Tasks
- [ ] Add failing tests for config loading, fixture loading, deterministic scoring, and CLI JSON output.
- [ ] Implement typed scoring dataclasses and pure scoring helpers.
- [ ] Add sample fixture categories and baseline/AIOS-shadow run artifacts.
- [ ] Wire `aios harness-eval run --config ... --json`.
- [ ] Add the v0 spec doc.
- [ ] Run targeted tests, context validation, and broader pytest where practical.
- [ ] Commit implementation, then update and commit `PROJECT.md`.
