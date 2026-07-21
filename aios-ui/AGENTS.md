# AIOS UI Agent Router

This directory contains the Next.js operator UI for AIOS.

Before non-trivial UI work:

1. Read `../.agents/context/README.md`.
2. Read `../.agents/context/ui.md`.
3. Use `pnpm` from `aios-ui/`.

## Local Rules

- Prefer Server Components and server helpers.
- Add `"use client"` only for hooks, browser APIs, or real interactivity.
- Use the `@/*` import alias.
- Respect `.dependency-cruiser.cjs` boundaries.
- Run `pnpm lint` and `pnpm lint:architecture` for meaningful UI changes.
