# NotebookLM MCP Routing Policy

NotebookLM MCP is a bounded source-synthesis and connection-discovery backend for AIOS. It is useful when an agent needs to reason over a selected packet of documents or discover relationships across a curated slice of the second brain. It is not the canonical second brain. Obsidian remains the durable human-readable memory layer, local stores remain the operational memory layer, and TMCP remains the agent-facing skill/context layer.

## Role

NotebookLM MCP is an optional synthesis appliance. AIOS selects a bounded source bundle first, then NotebookLM can synthesize over that bundle, and AIOS stages any useful output for review.

## Use NotebookLM MCP When

- The task involves synthesis across a bounded set of uploaded or selected sources.
- The task asks for comparison across documents.
- The task needs a source-grounded briefing, FAQ, study guide, digest, or onboarding brief.
- The task is about relationships, patterns, contradictions, or stale assumptions.
- The task asks what should become a TMCP module or reusable skill.
- The task asks what the user should learn next based on selected notes.
- The task asks how to organize a bounded area of the second brain.
- The task asks what old notes are relevant to a new project.

## Do Not Use NotebookLM MCP When

- The task only needs a source-of-truth lookup from Obsidian, local markdown, or TMCP.
- The task involves raw private operational logs, session traces, or telemetry.
- The task requires repo search, code edits, command execution, or tests.
- The task requires deterministic local state reconstruction.
- The source set is unbounded or the user asks to send the whole vault.
- The task involves secrets, credentials, raw logs, or sensitive personal content.
- The task depends on latest public information; use web search instead.

## Routing Decision Tree

1. Execution/code/filesystem task: use repo tools, shell, code search, and local files.
2. Source-of-truth memory lookup: use Obsidian, local markdown, or TMCP.
3. Raw operational/session/agent memory: use SQLite/local operational memory.
4. Compiled skill/workflow decision: use TMCP.
5. Bounded source synthesis over selected documents: use NotebookLM MCP.
6. Cross-note relationship, contradiction, or learning task: use local retrieval to select a bounded bundle, then use NotebookLM MCP for synthesis.
7. Public/current information: use web search.
8. If multiple routes apply: retrieve locally first, use NotebookLM only as synthesis, stage the output, and promote reviewed conclusions back into Obsidian/TMCP/project docs.

## Required Preflight Questions

- What source bundle is being sent?
- Why is NotebookLM better than local retrieval for this task?
- Is the source bundle bounded?
- Does the user expect source-grounded synthesis?
- Is this a fact lookup or a relationship/synthesis task?
- Is any sensitive or raw operational data included?
- Should the resulting synthesis be promoted back into Obsidian or TMCP?
- What provenance should be recorded?

## Source-Bundle Rules

AIOS must not dump the entire second brain into NotebookLM. Source bundles must include paths, titles, source types, inclusion reasons, sensitivity classes, and exclusions. Raw operational paths such as `logs/`, `data/`, and `.git/` are excluded by default.

## Provenance Rules

NotebookLM-assisted output records the source system, route type, bundle name/id, source count, notebook alias, query, timestamp, agent, reason for route, whether local retrieval ran first, destination, and promotion state. Logs should store references, hashes, file paths, aliases, notebook IDs, and bundle IDs instead of raw private source contents.

## Staging And Promotion

NotebookLM synthesis is staged before promotion. Durable knowledge goes to Obsidian after review. Agent-facing workflows go to TMCP after review. Implementation-specific decisions go to project docs after review. NotebookLM output must not overwrite canonical notes automatically.

## Failure Behavior

NotebookLM MCP is optional. If it is unavailable, AIOS continues with local retrieval and explains that NotebookLM synthesis was skipped.

## Supported Experimental Backend

AIOS recognizes `jacob_bd_notebooklm_mcp_cli` as an experimental backend contract from `jacob-bd/notebooklm-mcp-cli`. This backend is not an official Google NotebookLM API. It uses undocumented NotebookLM internal APIs and browser-cookie authentication according to its upstream documentation.

Required executables:

- `nlm`
- `notebooklm-mcp`

Required MCP tools:

- `server_info`
- `notebook_create`
- `source_add`
- `notebook_query`

AIOS must treat missing executables, missing auth, or failed MCP probing as `skipped_unavailable`.

## Automated Agent Use

Automated use is allowed only through the guarded adapter path:

1. Classify the task as a NotebookLM synthesis task.
2. Build and inspect a bounded source bundle.
3. Reject empty bundles, excluded-source bundles, sensitive sources, raw logs, and whole-vault requests.
4. Run `nlm login --check`.
5. Create or select the NotebookLM notebook.
6. Add approved sources with `--wait`.
7. Query NotebookLM.
8. Stage the output with provenance.

The adapter must not silently promote NotebookLM output into Obsidian, TMCP, or project docs.

## Example Decisions

- `What did I decide about TMCP shortcut skills?`: Obsidian/local/TMCP; do not use NotebookLM.
- `Resume the last agent session`: local operational memory; do not use NotebookLM.
- `Compare these 12 uploaded AI skill docs`: NotebookLM MCP over selected documents.
- `Use existing TMCP notes and this uploaded research packet`: local/TMCP first, NotebookLM second.
- `Search the whole repo for broken imports`: code search/filesystem.
- `Find hidden connections across AIOS memory notes`: local retrieval, NotebookLM connection discovery, stage results.
- `What should I learn next based on recent notes?`: local retrieval, bounded bundle, NotebookLM learning synthesis, stage output.
- `Find outdated assumptions in older architecture notes`: local retrieval, NotebookLM drift detection, stage report.
- `Send my entire second brain to NotebookLM`: reject unbounded dump and ask for a bounded topic.
