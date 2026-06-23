# Plan 21-07 Summary: TMCP Routing, Manifests, Provenance, And Dependency Maps

**Status:** Complete
**Requirement:** MACS-07
**Completed:** 2026-06-23

## What Changed

- Added `config/tmcp/macos-skills-router.json`.
- Added `config/skills/macos-manifest.json`.
- Added `docs/skills/macos-dependency-map.md`.
- Marked MACS-07 complete in `.planning/REQUIREMENTS.md`.

## Key Decisions

- Kept macOS routing as an intent-specific overlay with `always_loaded: false`.
- Used strict task IDs under `@task:macos.*` and module IDs under `@module:macos.*`.
- Recorded donor repository, commit, source paths, transformation type, freshness notes, license note, behavior tests, related modules, validation commands, and permission gates.
- Documented release routing as project detection -> release pipeline -> permission gate -> dry-run -> approval -> execution.

## Verification

- `node --input-type=module -e "const fs=await import('node:fs'); const manifest=JSON.parse(fs.readFileSync('config/skills/macos-manifest.json','utf8')); const router=JSON.parse(fs.readFileSync('config/tmcp/macos-skills-router.json','utf8')); const ids=[...manifest.nodes.map(n=>n.id),...manifest.modules.map(m=>m.id)]; if(new Set(ids).size!==ids.length) throw new Error('duplicate ids'); for (const node of [...manifest.nodes,...manifest.modules]) if(!fs.existsSync(node.path)) throw new Error(node.path); for (const route of router.routes) for (const ref of route.sequence.filter(v=>v.startsWith('@task:')||v.startsWith('@module:'))) if(!ids.includes(ref)) throw new Error(ref);"`
- `rg -n "@task:macos.project.detect|@task:macos.build.verify|@task:macos.patterns.route|@task:macos.settings.window|@task:macos.sparkle.auto_update|@task:macos.notch.overlay|@task:macos.release.pipeline|@module:macos.menu_bar|always_loaded|source_provenance|freshness_note|license_note" config/tmcp/macos-skills-router.json config/skills/macos-manifest.json docs/skills/macos-dependency-map.md`
- `pnpm context:validate`
- `git diff --check -- config/tmcp/macos-skills-router.json config/skills/macos-manifest.json docs/skills/macos-dependency-map.md .planning/REQUIREMENTS.md .planning/STATE.md .planning/phases/21-macos-native-app-skill-pack/21-07-SUMMARY.md`
