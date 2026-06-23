# Plan 21-02 Summary: Donor Repository Audit

**Status:** Complete
**Requirement:** MACS-02
**Completed:** 2026-06-23

## What Changed

- Added `docs/audits/macos-app-skills-audit.md`.
- Audited `fayazara/macos-app-skills` at commit `a60365ae85bfc3d1f2f8b260b080d77bfb2f3ec0`.
- Covered `README.md`, `skills.sh.json`, all donor `SKILL.md` files, Swift reference directories, and release CLI files.
- Marked MACS-02 complete in `.planning/REQUIREMENTS.md`.

## Key Decisions

- Adopt project detection, xcodebuild verification, native macOS pattern vocabulary, settings-window architecture, Sparkle lifecycle constraints, notch geometry concepts, and release checklist structure.
- Reject direct copying of broad all-in-one pattern guidance, donor release CLI behavior, and ready-to-commit reference Swift files.
- Transform donor material into a task-routed `config/tmcp/macos-native-app/` namespace with small modules, permission branches, provenance fields, and behavioral tests.
- Treat donor release CLI material as dry-run validation and safety-gate source material only.

## Verification

- `test -f docs/audits/macos-app-skills-audit.md`
- `rg -n "README.md|skills.sh.json|build/SKILL.md|macos-patterns/SKILL.md|settings-ui/SKILL.md|auto-update/SKILL.md|notch-ui/SKILL.md|release/SKILL.md|release/cli/main.go|Worth Adopting|Should Not Be Adopted Directly|Safety Risks|Freshness|Transformation|config/tmcp/macos-native-app|release_publish_gate|dry-run" docs/audits/macos-app-skills-audit.md`
- `pnpm context:validate`
- `git diff --check -- docs/audits/macos-app-skills-audit.md .planning/REQUIREMENTS.md .planning/STATE.md .planning/phases/21-macos-native-app-skill-pack/21-02-SUMMARY.md`
