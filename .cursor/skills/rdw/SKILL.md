---
name: rdw
description: >-
  Research-grounded domain writing pipeline (sports analytics, music criticism,
  technical copy, policy, etc.). Agent researches per skill instructions; then
  grounded draft, domain QA, humanizer. Use when /rdw or domain-specific copy
  must be factual. Not for style-only polish — use humanizer alone for that.
disable-model-invocation: true
---

# /rdw — Research domain writing

**Root:** `/Users/jakyeamos/AIOS/research-domain-writing`

## On invoke

1. Read `/Users/jakyeamos/AIOS/research-domain-writing/SKILL.md`, `config/router-inference.yaml`, `prompts/domain-router.md`, `prompts/pipeline-orchestrator.md`.
2. **Infer** domain, entity, output_type, audience, depth from the user's message (`key=value` only if they provide overrides).
3. Show inferred contract briefly; proceed unless they correct you.
4. Run the full pipeline. **You research** (tools/browser/files); skill structures packets.
5. Do not humanize before QA passes.
6. Save outputs under `/Users/jakyeamos/AIOS/research-domain-writing/outputs/` and report paths.

RDW is not omnipotent — it does not replace your repo tools or deploy copy; it produces grounded artifacts you apply.

## User message (minimal)

```
improve the copy on my LIS leaderboard
```

No other fields required.

## Also

- Batch: use skill `rdw-batch` or `/rdw-batch`
- Docs: `/Users/jakyeamos/AIOS/research-domain-writing/README.md`
