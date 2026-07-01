# AIOS Daily-Use Case Study

## Product Problem

AIOS exists because serious agent-assisted work has a repeated failure mode: the operator manually assembles project context, quality rules, workflow expectations, verification commands, and follow-up notes in every chat. That manual setup makes good work possible, but it is slow, inconsistent, and easy to lose after the session ends.

The release-ready daily-use claim is narrower than the full AIOS vision:

```text
AIOS turns a serious work objective into a governed route, context packet, run, evaluation trail, writeback state, and next action with less manual assembly than raw chat.
```

## Architecture Loop

The daily loop is intentionally small:

```text
doctor -> start-work -> daily-flow replay -> next-action -> closeout evidence
```

- `doctor` checks local release prerequisites: Python dependencies, SQLite reachability, local stores, pnpm-only JavaScript state, and the required daily-use command surface.
- `start-work` resolves the target project and workflow, creates a governed run, writes a briefing packet, and links the active invocation.
- `daily-flow --run-id` replays the objective through route, packet, run, evaluation, writeback, unresolved delta, and next action evidence without manual SQLite inspection.
- `next-action --project` ranks the follow-up work visible to the operator.

This preserves the existing AIOS pipeline rather than replacing it:

```text
route -> packet -> run -> evaluation -> writeback -> operator projection
```

## Safety Boundary

AIOS remains local-first. The primary stores are local files, local SQLite, local logs, and local project repositories. High-impact writebacks, workflow promotions, and linked-repo adoption work remain reviewable instead of silently becoming default behavior.

The daily-use release boundary is also intentionally conservative:

- Tiny edits and direct answers should not route through AIOS.
- Linked-repo portfolio certification is not the release centerpiece until AIOS itself is frictionless to use.
- Extracted packages may remain local path dependencies during active development, but `doctor` must make missing dependency state explicit.
- The UI is an operator surface over trusted state, not the source of truth.

## Release Evidence

The release contract is covered by behavior tests in `tests/test_aios_cli.py`:

- direct `bin/aios.py --help` smoke contract
- `health --json` structured health output
- `doctor --json` pass and package-manager-drift failure cases
- integrated daily loop: `start-work` creates route, packet, run, and invocation ids; `daily-flow --run-id` replays the eight canonical steps; `next-action --project` returns project-scoped follow-up work

The package-manager contract is enforced by aligning local and CI commands on pnpm:

- root `package.json` declares `packageManager`
- `aios-ui/package.json` declares `packageManager`
- `aios-ui/pnpm-lock.yaml` is the UI lockfile authority
- `.github/workflows/aios-ui-quality.yml` uses pnpm/corepack

## Known Limits

AIOS is not yet an open-source-ready product. It is a personal local operating layer with private paths, local stores, and incubating subsystems.

The next release-readiness work should stay focused on daily use:

- keep `doctor` actionable as extracted packages and local stores change
- make the daily loop the first README path and the first smoke test
- keep Phase 29 linked-repo remediation behind AIOS self-readiness
- avoid polishing UI surfaces that cannot drill down to route, packet, run, evaluation, writeback, or next-action evidence
