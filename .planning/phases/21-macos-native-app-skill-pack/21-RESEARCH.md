# Phase 21: macOS Native App Skill Pack - Research

**Gathered:** 2026-06-04
**Status:** Ready for planning

<source_spec>
## Source Spec

Phase 21 is specified in the pasted "AIOS skill-system upgrade" prompt ingested on 2026-06-04. The spec asks AIOS to audit `https://github.com/fayazara/macos-app-skills`, extract durable native macOS app development patterns, and transform them into AIOS/TMCP-compliant skills without blindly copying the donor format.

The donor repository is source material. The target output is an AIOS-native platform skill pack with task-first routing, strict decision trees, environment detection, permission gates, provenance metadata, behavioral tests, validation commands, conflict detection, TMCP router integration, reusable semantic modules, minimal context loading, and repair recommendations.
</source_spec>

<domain>
## Phase Boundary

Phase 21 creates a domain-specific platform skill pack for native macOS app development. It is not a general skill portfolio import and not a native command pack.

It overlaps earlier phases but has a distinct platform-domain boundary:

- Phase 15 handles general agent skill portfolio integration and external library comparison.
- Phase 17 provides capability-pack routing and mode patterns.
- Phase 19 provides native command safety and logging patterns.
- Phase 20 provides execution-symmetric planning and skill-as-planning-lens behavior.

Phase 21 focuses on macOS project/build detection, xcodebuild verification, native pattern modules, settings windows, Sparkle updates, notch overlays, release/signing/notarization/appcast safety, TMCP routing, provenance manifests, behavioral tests, and validation.
</domain>

<requirements>
## Phase 21 Requirements

### MACS-01: AIOS Skill System Audit
AIOS must audit current skill, instruction, router, TMCP, manifest, validation, provenance, dependency-map, permission-gate, and behavioral-test conventions before adding macOS skills.

### MACS-02: Donor Repository Audit
AIOS must inspect the donor repository material and produce `docs/audits/macos-app-skills-audit.md` covering donor summary, adoption candidates, direct-copy rejections, AIOS compatibility gaps, safety risks, freshness/version risks, transformed skill/module list, TMCP routing changes, and implementation checklist.

### MACS-03: macOS Project Detection And Build Verification
AIOS must add task-shaped skills for macOS project detection and xcodebuild verification, including workspace/project/package detection, scheme discovery, Xcode/SDK/DEVELOPER_DIR checks, destination/configuration selection, signing-disabled fallback, error parsing, repair recommendations, and post-fix rebuild requirements.

### MACS-04: Native macOS Pattern Router And Modules
AIOS must split donor macOS pattern knowledge into small semantic modules loaded only when relevant, including menu bar, window/panel, screen geometry, keyboard shortcuts, file picker, pasteboard, drag/drop, navigation/inspector, launch/login, Quick Look/workspace, ScreenCaptureKit, and UserDefaults/AppStorage patterns.

### MACS-05: Settings, Sparkle, And Notch Skills
AIOS must add guarded skills for native settings windows, Sparkle auto-update support, and notch-style overlays, each with environment guards, permission gates, architecture preservation, validation commands, fallback behavior, and repair recommendations.

### MACS-06: macOS Release Pipeline Skill
AIOS must add a dry-run-first macOS release pipeline skill with hard permission gates for git, GitHub release, appcast mutation, signing, notarization, publishing, and version/build changes. It must validate DMG, signatures, appcast XML, release URL, duplicate build numbers, and secret safety.

### MACS-07: TMCP Routing, Manifests, And Provenance
AIOS must add or update TMCP routing, strict node IDs, manifests, dependency maps, related-module pointers, source provenance, source freshness/version notes, transformation type, license notes, and audited date for every skill/module.

### MACS-08: Behavioral Tests And Validation Command
AIOS must add behavioral tests for project detection, build verification, native pattern routing, settings UI, Sparkle, notch overlay, and release safety. It must add or extend a validation command that checks IDs, TMCP pointers, modules, provenance, permission gates, behavioral tests, private-key patterns, broad triggers, and release publish gates.

### MACS-09: Documentation And Final Report Workflow
AIOS must document the macOS skill pack, routing behavior, safety gates, validation command, future platform-skill pattern, donor pattern note, assumptions, adopted/changed/rejected donor ideas, remaining risks, and final implementation report format.
</requirements>

<plan_sequence>
## Recommended Plan Sequence

- **21-01**: Audit existing AIOS skill/TMCP/router/manifest/test/provenance conventions.
- **21-02**: Audit donor repository and write transformed skill/module map.
- **21-03**: Implement macOS project detection and build verification skills.
- **21-04**: Implement native macOS pattern router and semantic modules.
- **21-05**: Implement settings window, Sparkle auto-update, and notch overlay skills.
- **21-06**: Implement macOS release pipeline skill.
- **21-07**: Add TMCP routing, manifests, provenance, dependency maps, and node IDs.
- **21-08**: Add behavioral tests and validation command/script.
- **21-09**: Add documentation and final validation/reporting workflow.
</plan_sequence>

<implementation_constraints>
## Implementation Constraints

- Do not blindly copy donor files without transformation.
- Do not install third-party dependencies unless required by existing repo tooling.
- Do not run release commands.
- Do not commit, push, publish, notarize, sign, or mutate appcast files during implementation.
- Do not modify user project files outside this repo.
- Do not create broad, always-loaded macOS context.
- Do not store secrets or private Sparkle keys.
- Do not use destructive commands without explicit permission.
- Do not fabricate SDK behavior.
- Preserve source-specific useful knowledge while splitting broad material into task-routed modules.
- Add strict routing, validation, provenance, tests, assumptions, and repair recommendations.
</implementation_constraints>
