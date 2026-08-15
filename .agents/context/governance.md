# AIOS governance

Last reviewed: 2026-08-15

- Root `AGENTS.md` owns the repository hard stops and routing rules.
- Governed `/aios` routing failures remain blocking unless the user explicitly authorizes a bypass.
- Ordinary AIOS shadow output is comparison evidence. Do not merge, copy, or promote it without explicit review.
- Success criteria, approvals, run state, evaluation findings, and writebacks must remain registry- or database-backed and inspectable through the documented CLI.
- Changes to commands, agent-facing contracts, schemas, generated catalogs, or UI mirrors require the corresponding documentation, tests, and generated surfaces in the same reviewable change.
- Do not restore a mandatory project-truth workflow. Project notes are optional; current behavior is established by executable evidence and reviewed artifacts.
- Keep local-first data and credentials out of version control. Do not add static deployment tokens.
