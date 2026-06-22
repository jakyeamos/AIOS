# Task: Repo Detect

Task ID: `@task:repo_detect`

## Trigger

Use when the agent needs to identify the repository shape, stack, command surface, package manager, tests, build system, or architectural boundaries.

## Required Modules

- `@module:tool_safety`
- `@module:command_discovery`

## Instructions

1. Inspect root files first: agent instructions, package metadata, lockfiles, pyproject, Makefile, CI configs, and README.
2. Prefer fast search commands and file lists over broad reads.
3. Identify command candidates without running expensive or mutating commands.
4. Preserve repo-local conventions over generic defaults.
5. Output a concise stack profile, command map, and risks.

## Exit

Exit when the agent can name the stack, package manager, relevant validation commands, and files likely to matter for the user task.

