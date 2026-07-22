# Public Skill Mining Disposition Ledger

**Date:** 2026-07-22
**Purpose:** Record the first-party skill and workflow mining pass that promotes
portable behavior into `jakyeamos-agent-skills` while preserving AIOS as an
archival/internal runtime source.

## Decision

`jakyeamos-agent-skills` is the canonical distribution catalog for portable,
redistributable skills. `AIOS/skills-library` remains a historical generated
graph for AIOS-local traversal and provenance. It is not the public promotion
authority.

This ledger is private because it contains source paths and worktree state. The
public repository contains only logical source classes and sanitized
dispositions.

## Raw Inventory Coverage

The generated discovery report remains the exhaustive raw inventory: 2,848
candidate files, 1,703 reusable-skill candidates, 851 workflow prompts, 13
global instruction files, 75 project-specific instruction files, and 13 unsafe
or secret-like files. Duplicate paths are folded into source and behavior
groups below rather than copied one-for-one.

| Source root | Tracked files | Candidate paths | Dirty | Disposition coverage |
| --- | ---: | ---: | ---: | --- |
| AIOS | 1,785 | 865 | 0 | authored workflows, runtime boundaries, generated corpus |
| BBDSE | 676 | 372 | 0 | product/domain material reviewed and excluded unless generalized |
| BIP-Console | 133 | 101 | 6 | product material; read-only inspection |
| Bballedu | 470 | 119 | 0 | product/domain material reviewed |
| BidCamp | 3,182 | 2,325 | 2 | product/brand material; read-only inspection |
| Book | 255 | 39 | 0 | product/content material reviewed |
| Book-documents-github | 141 | 31 | 0 | product/content material reviewed |
| Crimclock | 563 | 241 | 2 | legal/product material excluded |
| Dsci-proj | 312 | 18 | 0 | project material reviewed |
| EliHealth | 436 | 177 | 1 | product material; read-only inspection |
| Fantasy | 705 | 256 | 3 | product/domain material excluded |
| Hoopscout | 215 | 107 | 2 | product/domain material excluded |
| LaxDS | 124 | 52 | 0 | project material reviewed |
| R-Project | 135 | 43 | 3 | project material; read-only inspection |
| Terrace | 4,121 | 3,907 | 0 | existing public Terrace router; duplicates folded |
| Terrace-gpt56-modernization | 4,179 | 3,930 | 0 | duplicate Terrace source; folded into existing router |
| Vaults | 575 | 5 | 21 | private notes excluded from public mining |
| agent-eval-contract | 76 | 16 | 0 | external contract reference |
| agent-eval-runtime | 12 | 0 | 0 | runtime reference only |
| agent-router | 120 | 67 | 0 | reusable routing concepts reviewed |
| ai-context-runtime | 12 | 0 | 0 | external runtime reference |
| ai-workflow-leverage | 51 | 5 | 3 | verified-fix and change-map behavior promoted |
| amos-saas | 830 | 512 | 4 | product material; read-only inspection |
| career-ops | 441 | 49 | 2 | private/domain safety boundary; excluded |
| claude-config | 36 | 9 | 17 | low-always-loaded migration promoted; source untouched |
| claude-improvement-lab | 24 | 8 | 0 | workflow concepts reviewed |
| context-compiler-contract | 18 | 8 | 0 | external contract reference |
| dispatches-from-cyberspace | 241 | 44 | 3 | product/content material reviewed |
| dotfiles | 31 | 22 | 1 | host-managed configuration excluded |
| eslint-plugin-anti-slop | 112 | 33 | 1 | quality concept reviewed; runtime external |
| frmwrklabs | 53 | 9 | 0 | project material reviewed |
| greenlight | 73 | 5 | 0 | external/product scanner reference |
| jakyeamos-agent-skills | 72 | 49 | 0 | canonical public target |
| jakyeamos-profile | 11 | 8 | 0 | private profile material excluded |
| mac-control | 29 | 1 | 8 | host-control material excluded |
| manga-sync | 13 | 8 | 0 | project material reviewed |
| marketing-autoresearch | 39 | 0 | 0 | product/runtime material reviewed |
| portfolio | 149 | 47 | 0 | private/public-content boundary; excluded |
| pre-cr-suite-lsp | 176 | 20 | 0 | external product skill reference |
| quality-evidence-contract | 19 | 8 | 0 | historical/external contract reference |
| quality-runner | 516 | 75 | 0 | external quality runtime reference |
| relay | 37 | 0 | 0 | product/runtime material reviewed |
| remodelvision | 154 | 56 | 4 | product material; read-only inspection |
| repo-quality-certifier | 26 | 9 | 0 | historical/external quality reference |
| research-domain-writing | 327 | 36 | 0 | existing public skill/project |
| soundscape-app | 5,637 | 2,660 | 0 | duplicate product corpus; excluded |
| soundscape-gpt56 | 6,043 | 2,912 | 0 | duplicate product corpus; excluded |
| tenure | 4,629 | 2,312 | 0 | product/legal material excluded |
| tm | 73 | 11 | 3 | project material; read-only inspection |
| tmcp | 278 | 88 | 0 | portable harvest/analysis contracts promoted; runtime external |
| untitled1 | 15 | 8 | 0 | project material reviewed |
| video-pipeline | 255 | 17 | 0 | project material reviewed |

Dirty source roots were inspected read-only. No source changes were staged,
restored, stashed, or overwritten during mining.

## Candidate Dispositions

| Candidate | Evidence family | Disposition | Public treatment |
| --- | --- | --- | --- |
| low-always-loaded-instruction-migration | multi-runtime manifest, layers, conflict ledger, drift/install audit | promote | new portable skill and supporting workflow |
| skill-harvest-and-promotion | TMCP harvest/gap analysis plus AIOS skillification design | promote | new portable skill and promotion rubric |
| repo-behavior-spec-loop | AIOS behavioral loop plus TMCP skill contract | promote | new portable skill and tabular behavior fixture |
| review-gated-verified-fix | leverage issue admission, disposable worktree, explicit gates, review packet | promote | new portable skill and review packet template |
| evidence-backed-change-surface-mapping | bounded change map, freshness, unknown paths, provenance | promote | new portable skill; strengthen environment audit |
| agentized-task-packet | AIOS request compiler and targeted context/verification contract | promote | new portable skill and packet schema |
| durable-agent-workflows | durable workspace, goal, artifact, steering, queueing, stopping rules | promote | new portable skill and workflow contract |
| divergent-strategy | candidate portfolio, judges, entropy, promotion gates | promote | specialized beta skill |
| operating-language | canonical vocabulary and observable leading-word test | promote | specialized beta skill |
| macOS build/release verification | authored transformation of donor-derived material | defer | license/provenance gap; retain private/reference-only |
| orchestrated-subagent-development | AIOS orchestration roles and routing | merge | supporting reference under agentized-task-packet |
| quality/evidence gates | Quality Runner, Pre-CR, repo certification | merge/reference | strengthen evaluation-evidence; keep runtimes external |
| Terrace workflow corpus | duplicate command-level skills | merge | retain one existing Terrace router |
| Research Domain Writing | existing public project and skill | retain | no duplicate skill |
| career, legal, portfolio, product, and personal workflows | domain/private content | exclude | no public redistribution |
| generated AIOS/TMCP harvest output | generated, path-bearing, duplicate wrappers | exclude | provenance only; never copied |
| vendor/plugin/cache content | third-party or host-managed | exclude/reference | no redistribution or implicit install |

There are no unclassified candidate groups in this pass. Individual raw paths
inherit the disposition of their source behavior group; ambiguous candidates
remain deferred in this ledger rather than being silently promoted.

## Promotion Gate

A candidate is promotable only when it is first-party or license-cleared,
reusable beyond one product, has a trigger and non-trigger, defines inputs and
outputs, exposes a verifier and stopping condition, states safety boundaries,
and can be forward-tested with sanitized fixtures. A complete user-requested
workflow with strong cross-runtime reuse may qualify even before a second
independent repository adoption; this exception applies to the
low-always-loaded migration.

## Verification Expectations

The public catalog must pass its skill validator, catalog validator, public
safety scan, clean-room installer tests, and forward tests for every promoted
skill. Public provenance uses logical source IDs only. The generated AIOS graph
must remain readable by existing internal consumers after the redirect marker
is added.
