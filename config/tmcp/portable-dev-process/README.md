# Portable Dev Process TMCP Pack

This pack is a portable subset of AIOS development-process behavior. It is meant to be vendored into other repositories without AIOS runtime services, databases, eval archives, or continuous-improvement requirements.

Inside AIOS, this is not the canonical local skill graph. The default local TMCP graph is `skills-library/skills.tmcp`, generated from the harvested canonical skills library. This pack is a namespace overlay for portable development-process behavior.

Use this pack when a project needs practical agent development help:

- repo and stack discovery
- command discovery
- quality checks
- debugging
- diff review
- test planning and generation
- git hygiene
- CI triage
- frontend verification
- visual polish for product UI, enterprise SaaS screens, interaction architecture, AI surfaces, print/PDF reports, and realistic demo data
- dependency audit
- hook installation guidance

For this portable pack, the machine-readable graph is `manifest.json`. Agents using the pack directly should start at `router.md`, load only the task and modules that change behavior for the current request, and stop once they have a minimal custom skill packet.

When this pack is installed inside AIOS, it is registered through `config/tmcp/registry.json` as the `portable_dev_process` namespace. That registry makes this pack traversable from the broader canonical TMCP graph without making namespace boundaries hard access limits.

Default use is read-only: do not edit files, install hooks, install dependencies, commit, push, or perform destructive actions without explicitly asking the user or receiving an explicit user request.

The visual polish path is portable by default. Product-specific branches such as Tenure visual identity, BidCamp visual identity, and Framework Labs editorial identity are optional overlays and should not be loaded for generic boilerplate polish unless the active project or user request selects them.

Some visual-polish nodes are distilled from user-supplied source files rather than copied wholesale. The distilled sources are cited inside each module or branch. Keep these nodes behavior-focused: preserve rules that change implementation, review, or routing decisions; omit long examples, decorative prose, and source-specific copy that would not change agent behavior.

## Non-Goals

- Do not require AIOS SQLite state.
- Do not require AIOS-only writebacks.
- Do not require AIOS eval records.
- Do not require GSD/Terrace planning artifacts.
- Do not mutate a host repository unless the user explicitly asked for implementation or hook installation.
