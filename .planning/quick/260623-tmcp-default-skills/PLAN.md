# Quick Task 260623: TMCP Default Skills

## Task

Make clear that repo-vendored skills should default through the canonical local TMCP graph and wire the new operating-language skill into that path.

## Scope

- Preserve `skills-library/skills.tmcp` as the default local TMCP graph.
- Treat `config/tmcp/portable-dev-process` as an overlay, not a competing default graph.
- Add runtime routing for operating-language objectives to `@module:operating_language`.
- Add the local generated graph module for operating language.
- Update truth/docs and focused tests.

## Verification

- Run focused TMCP runtime tests.
- Run context validation.
