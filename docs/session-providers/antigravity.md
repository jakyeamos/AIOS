# Antigravity Session Provider

## What Is Imported

The Antigravity provider imports local operational metadata from:

- `~/.gemini/antigravity-cli/brain/**`
- `~/.gemini/antigravity-cli/plugins/**`
- `~/.gemini/GEMINI.md`
- Antigravity/Gemini config, log, cache, and session files under supported local roots

It extracts task, repository/workspace, commands, files touched, decisions, failures, and outcomes.

## What Is Not Imported

Raw reasoning traces, chain-of-thought content, unknown binary content, and full private transcripts are not imported as content. Unknown binary files are represented only by metadata pointers and health warnings.

## Default Paths By OS

- macOS/Linux: `~/.gemini/**` and `~/.config/Antigravity/**`
- Other platforms: add platform-specific config roots before enabling broad scans.

## Privacy And Security

Reasoning traces are pointer-only. The provider stores path, mtime, size, content hash, and extraction status for unsafe artifacts. Summaries and writebacks contain only operational metadata.

## Backfill

```bash
python3 ~/AIOS/bin/sessions.py backfill --provider antigravity
```

## Incremental Sync

```bash
python3 ~/AIOS/bin/sessions.py sync --provider antigravity
```

## Debug Provider Health

```bash
python3 ~/AIOS/bin/sessions.py debug --provider antigravity
```

Debug output includes source type counts and metadata-only warnings without private content.

## Disable

Remove `antigravity` from `session_providers.enabled` in `config/session-provider-config.yaml`.

## Add Another Provider

Implement `SessionProvider`, preserve raw/private content boundaries, register the provider, and add fixtures covering source discovery, parsing, normalization, and redaction.
