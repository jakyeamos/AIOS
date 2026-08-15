# AIOS UI

Last reviewed: 2026-08-15

- Work from `aios-ui/` or use `pnpm --dir aios-ui ...` from the repository root.
- Follow `aios-ui/AGENTS.md`: prefer Server Components, add `"use client"` only for browser behavior, and use the `@/*` alias.
- Preserve the dependency-cruiser boundaries across `app`, `components`, `lib`, and `server`.
- Prompt and workflow registries generate `aios-ui/server/generated/prompt-catalog.ts` and `workflow-catalog.ts`; run both generation checks before build.
- Meaningful UI changes require lint, TypeScript, architecture, build, and direct browser verification at the affected route.
- The primary local surface is `http://localhost:3000`; Next.js may select another port when 3000 is occupied.
