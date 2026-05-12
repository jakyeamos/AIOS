---
id: global.security
title: Global Security Standard
tier: global
scope:
  - all_projects
priority: immutable
status: active
summary: Baseline security expectations for all AIOS-managed work.
applies_when:
  - task_touches_auth
  - task_touches_api_keys
  - task_touches_user_data
  - task_touches_permissions
load_if_matched:
  - packets/security.oidc-secrets.md
tags:
  - security
  - secrets
  - auth
  - privacy
conflicts:
  protected_topics:
    - secrets
    - privacy
    - permissions
  resolution: More specific project rules may add constraints but cannot weaken this file.
last_reviewed: 2026-05-12
---

Avoid static secrets, unchecked permissions, and privacy-weakening shortcuts.
Prefer secretless or short-lived credential flows for deployment and automation work.
Treat user data, vault data, prompts, and run history as sensitive by default.
Security findings should be recorded rather than silently accepted.

## Applicability

- Load for auth, API keys, OIDC, deployment credentials, privacy, permissions, or personal data.
- Load linked packets when deployment secrets or OIDC are mentioned.

## Acceptance Criteria

- No new static secret path is introduced.
- Sensitive context is scoped to the task and receipt.
- Security tradeoffs are explicit writeback candidates when unresolved.
