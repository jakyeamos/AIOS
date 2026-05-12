---
id: domains.web-apps
title: Web Apps Domain Standard
tier: domain
scope:
  - web_app_projects
priority: high
status: active
summary: Routing standard for Next.js, React, dashboard, and deployment work.
applies_when:
  - task_touches_web_app
  - task_touches_design
tags:
  - web
  - nextjs
  - react
  - deployment
last_reviewed: 2026-05-12
---

Web-app work should preserve strict TypeScript boundaries and existing UI conventions.
Use Server Components by default and client components only for interactivity.
Deployment work must preserve security and observability signals.

## Applicability

- Load for AIOS UI, Next.js, React, dashboard, deployment, or browser-facing tasks.
- Pair with security when OIDC, secrets, auth, or permissions are involved.

## Acceptance Criteria

- User-facing state is source-backed and inspectable.
- UI changes follow the existing component and routing patterns.
