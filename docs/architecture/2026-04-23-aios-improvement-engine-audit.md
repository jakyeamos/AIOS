# AIOS Improvement Engine Audit (Phase 1c, Audit-Only)

Date: 2026-04-23  
Status: Completed decision memo (no implementation changes by design)

## 1. Executive Verdict

The cron-first, mostly non-LLM vision is partially viable for AIOS today, but only for operational hygiene and objective checks. AIOS already has scheduled orchestration (`bin/aios-pipeline.py`, `bin/cron-ingest-codex.py`), experiment/run persistence (`experiments`, `lab_runs`, `improvement_writebacks`), and rule scoring/promote flows. That supports deterministic ingestion, scoring, and benchmark execution.

It breaks down at the point where "quality improvement" needs semantic judgment. Current loops can measure run success, deltas, and some performance signals, but they do not yet produce reliable, task-family quality judgments that justify automated promotion at scale. High-confidence recommendation: choose a **hybrid path** now, with deterministic cron loops for objective gates and selective human/LLM judging for qualitative promotion decisions.

## 2. Current State Assessment

### Strengths
- Scheduled execution exists and is used:
  - `bin/aios-pipeline.py` (daily phased cron-compatible orchestrator)
  - `bin/cron-ingest-codex.py`
- Experiment entities and lifecycle primitives exist:
  - `bin/run-experiment.py`
  - `schema.sql` / `data/schema.sql`: `experiments`, `improvement_writebacks`, `improvement_writeback_events`
- Lab benchmark automation exists for rule candidates:
  - `bin/trigger-lab-experiment.py`
- Runtime observability/control-plane has improved materially:
  - orchestration run/invocation/event tables
  - writeback and consistency/success-criteria evaluators

### Weaknesses
- Experiment lifecycle is not unified end-to-end:
  - `run-experiment.py` is manual CLI lifecycle, weak linkage to run families and promotion policy.
- Prompt experimentation is still early:
  - Phase 1 prompt library is now seeded and validated, but promotion remains manual and evidence capture is lightweight.
- Rule experimentation is coupled to specific lab mechanics:
  - not yet generalized into reusable regression suites per domain/task family.
- Deterministic evaluation coverage is strong for structure/process but weak for semantic output quality.

### Missing or misleading areas
- "We have experiments" is true at storage/CLI level, but not yet a reliable compounding quality engine.
- Benchmark representativeness is not yet guaranteed across real production-like failure distributions.
- Promotion confidence can still be overestimated when metrics are narrow or proxy-heavy.

## 3. Ideal State

An ambitious-but-realistic ideal for AIOS improvement is:
- deterministic scheduled loops for ingestion, baseline checks, regressions, schema/policy conformance, and cost/latency drift;
- benchmark corpora derived from real failures, sampled by task family and risk tier;
- versioned prompt/rule/strategy artifacts with explicit state transitions (`draft -> experimental -> shadow -> canary -> validated`);
- unified experiment records linking:
  - hypothesis
  - baseline/challenger configuration
  - evaluation evidence
  - promotion/rollback decision and actor;
- strict separation:
  - objective checks (deterministic pass/fail)
  - qualitative grading (human/LLM with explicit rubric);
- cheap continuous cron runs for objective gates, with selective qualitative review only where objective gates pass.

## 4. Delta Analysis

| Capability Area | Current (/10) | Ideal (/10) | Delta | Why Gap Matters |
|---|---:|---:|---|---|
| Scheduled experimentation infrastructure | 7 | 9 | Unified identity/retry/comparability across all experiment types | Cron runs exist, but experiment orchestration is still partially fragmented |
| Prompt experimentation system | 4 | 9 | Lifecycle + replay/shadow/canary + robust promotion evidence | Prompt library exists; promotion confidence loop is still mostly manual |
| Rule experimentation system | 6 | 9 | Generalized regression harness + safer promotion criteria | Lab pipeline exists but is specialized and not fully reusable across rule classes |
| Evaluation system | 5 | 9 | Better semantic quality measures and calibrated rubrics | Current deterministic metrics risk proxy optimization |
| Improvement loop integrity | 5 | 9 | Stronger failure-to-benchmark feedback and representative datasets | Data is collected; compounding improvement proof is still limited |
| Operational architecture | 7 | 9 | Tighter control-plane integration and reproducible experiment envelopes | Good primitives exist; orchestration of improvement lifecycle not fully unified |
| Cost/speed/complexity tradeoffs | 6 | 9 | Explicit budget guardrails and staged review triggers | Risk of overbuilding experiment machinery before quality signal is strong |

## 5. What Can Run Without an LLM

### Definitely should be deterministic
- schedule and execute recurring jobs (`aios-pipeline`, ingest, scoring, report generation)
- schema/contract checks, policy conformance, structural lint/tests
- run metadata capture, trend aggregation, regression alert thresholds
- objective benchmark scoring where verifier outputs are stable and meaningful

### Can be deterministic with effort
- task-family benchmark set maintenance (selection/sampling heuristics)
- replay and shadow run orchestration plumbing
- promotion guardrails based on objective gate bundles

### Probably should remain hybrid
- promotion decisions combining objective metrics and practical impact
- contradiction/exception triage for borderline experiments
- prompt/rule revision proposals from failed runs

### Fundamentally needs LLM/human judgment
- semantic quality deltas (clarity, usefulness, nuanced correctness) for open-ended tasks
- safety/completeness judgment when output quality is not reducible to exact structural checks
- deciding when a measured gain is worth operational complexity

## 6. Failure Modes and False-Confidence Risks

- **Proxy gaming:** improving easy metrics (latency, format compliance) while user-facing quality stagnates.
- **Narrow benchmark bias:** candidate wins on lab slices but regresses on real heterogeneous tasks.
- **Automation theater:** frequent cron runs that generate activity/logs but no policy-changing improvement.
- **Over-promotion:** treating inconclusive or weak evidence as durable improvement.
- **Maintenance drag:** expanding lifecycle complexity faster than evaluation confidence improves.

## 7. Decision Memo

### Path A: Lean deterministic
- Benefits: low cost, high reliability, quick operational hardening.
- Risks: limited semantic quality improvement; may plateau.
- Engineering complexity: low.
- Likely ROI: high short-term, medium long-term.
- Best when: team wants immediate stability and low operational burden.

### Path B: Hybrid
- Benefits: combines deterministic leverage with high-signal qualitative judgment where needed.
- Risks: requires disciplined rubric design and review governance.
- Engineering complexity: medium.
- Likely ROI: highest overall for current AIOS maturity.
- Best when: system has partial infrastructure (AIOS today) and needs compounding quality without overbuilding.

### Path C: LLM-heavy
- Benefits: faster semantic iteration and broader exploratory adaptation.
- Risks: higher cost, weaker reproducibility, larger trust burden.
- Engineering complexity: high.
- Likely ROI: volatile; only strong if review quality and budgets are tightly managed.
- Best when: deterministic signals are weak and budget for heavy judge loops is acceptable.

## 8. Recommended Path

Choose **Path B (Hybrid)**.

Reasoning:
- AIOS already has enough deterministic substrate to run objective gates cheaply.
- It does not yet have sufficiently trustworthy semantic evaluators to automate promotion decisions end-to-end.
- Hybrid gives immediate leverage from cron-first infrastructure while preventing false confidence from proxy-only scoring.

## 9. Sequenced Next Steps

1. Standardize experiment envelope fields across `run-experiment`, lab runs, and writebacks (identity, hypothesis, baseline/challenger, verdict evidence).
2. Define a minimal quality rubric per top task families with explicit objective vs subjective split.
3. Add deterministic pre-promotion gate bundle (schema/policy/structural/regression).
4. Require selective qualitative review for candidates that pass objective gates.
5. Track post-promotion drift and rollback triggers by task family, not only global metrics.

## 10. Brutal Truth

The current system is closer to "good instrumentation + partial automation" than a true self-improving engine. You are probably overestimating how much semantic quality improvement cron jobs can deliver without a hard rubric and review discipline. You are underestimating the operational tax of maintaining complex experiment lifecycles before the evaluation signal is trustworthy.
