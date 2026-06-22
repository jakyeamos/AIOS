# Task: Dependency Audit

Task ID: `@task:dependency_audit`

## Trigger

Use for dependency upgrades, package audits, lockfile changes, package-manager detection, version conflicts, or vulnerability triage.

## Required Modules

- `@module:dependency_policy`
- `@module:command_discovery`

## Instructions

1. Identify the package manager from lockfiles and project instructions.
2. Never switch package managers unless the project explicitly asks.
3. Separate direct dependencies from transitive dependencies.
4. Request network approval before commands that fetch registry data.
5. Run relevant tests or builds after dependency changes.

## Exit

Exit with dependency findings, safe command list, and verification plan.

