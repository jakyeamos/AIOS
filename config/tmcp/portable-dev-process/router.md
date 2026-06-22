# Portable Dev Process Router

This router builds a minimal custom skill packet from practical AIOS-derived developer tools. It intentionally excludes AIOS governance loops, truth-file writebacks, eval archives, and continuous-learning requirements.

Allowed traversal actions: LOAD, CONSIDER, USE, SKIP, EXIT, WHY, EVIDENCE, OUTCOME.

## Start

LOAD `manifest.json`.

USE `@branch:read_only_default` unless the user explicitly asked for implementation, hook installation, dependency changes, commits, or other mutation.

## Task Routing

- IF the request asks what repo this is, what stack it uses, or which commands exist, LOAD `@task:repo_detect`.
- IF the request asks to run lint, typecheck, tests, build, or verification, LOAD `@task:quality_check`.
- IF the request reports a bug, failure, flaky behavior, regression, or error output, LOAD `@task:debug_failure`.
- IF the request asks for a review, staged diff assessment, PR assessment, or risk scan, LOAD `@task:review_diff`.
- IF the request asks for tests or coverage, LOAD `@task:add_tests`.
- IF the request asks about CI or failed checks, LOAD `@task:ci_triage`.
- IF the request asks for browser, UI, screenshot, visual, or frontend runtime verification, LOAD `@task:frontend_verify`.
- IF the request asks for visual polish, product UI polish, enterprise SaaS presentation, dashboard polish, AI UI trust treatment, or realistic demo data, LOAD `@task:visual_polish`.
- IF the request asks to commit, branch, stage, inspect dirty state, or install hooks, LOAD `@task:git_hygiene`.
- IF the request asks about packages, dependency upgrades, lockfiles, or audits, LOAD `@task:dependency_audit`.
- IF the request asks for README, changelog, release notes, or developer docs, LOAD `@task:docs_update`.

## Cross-Task Edges

- CONSIDER `@task:repo_detect` before any task that needs unknown commands or stack.
- CONSIDER `@task:quality_check` after implementation, dependency, frontend, or test changes.
- CONSIDER `@task:debug_failure` when quality checks fail and the user wants a fix.
- CONSIDER `@task:review_diff` before commit-oriented work.
- CONSIDER `@task:visual_polish` after frontend generation when the screen looks generic, overly decorative, too card-heavy, or visually inconsistent with the target product.
- CONSIDER `@branch:tenure_visual_identity` only when the active project is Tenure or the user explicitly asks for Tenure-specific visual polish.
- CONSIDER `@branch:network_required` before dependency install, remote CI lookup, package audit, or docs that need current external facts.
- CONSIDER `@branch:destructive_action` before file deletion, history rewriting, force push, clean, reset, or generated artifact cleanup.

## Exit

EXIT after selecting the smallest set of task nodes, modules, and branches that changes behavior for the request. Record skipped plausible nodes with one-line reasons when producing a traversal receipt.
