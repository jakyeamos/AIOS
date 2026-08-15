# AIOS context compiler

Last reviewed: 2026-08-15

- `tools/context-compile.mjs` validates and compiles the file-backed context tree under `aios/context/`.
- `aios/context/index.md`, `router.md`, and `schema.md` are the always-loaded compiler contracts.
- `aios/context/.context/README.md` is the colocated module index required by the repository router.
- `context-compiler-contract` is a sibling workspace dependency declared as `file:../context-compiler-contract`; keep the package manifest and lockfile portable together.
- Generated briefings live under `aios/context/compiled/`; receipts live under `aios/context/receipts/`. Generated artifacts are evidence, not durable product truth.
- Validate with `pnpm context:validate` and `pnpm test:context`. For a concrete task, inspect `pnpm context:compile --task "<objective>"` and its loaded/skipped receipt.
