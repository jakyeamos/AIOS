---
id: packets.security.oidc-secrets
title: OIDC Secretless Deployment Packet
tier: packet
scope:
  - all_projects
priority: high
status: active
summary: Deep-enough packet for routing deployment secret work toward short-lived OIDC credentials.
applies_when:
  - task_touches_auth
  - task_touches_api_keys
tags:
  - oidc
  - secrets
  - deployment
  - security
last_reviewed: 2026-05-12
---

Prefer OIDC or other short-lived identity federation for deployments instead of long-lived static API keys.
Store only references, provider configuration, and audit evidence in AIOS context.
If a target platform cannot support OIDC, record a reviewed exception and expiry.

## Acceptance Criteria

- No static deployment secret is introduced as the default path.
- Provider, subject, audience, and permission scope are explicit.
- Exceptions include owner, reason, review date, and removal path.
