Act as the final independent adversarial reviewer for the corrected three-task
live paired benchmark. Do not modify repository or benchmark files. The prior
review found a missing treatment artifact; ignore the superseded original pair
for scoring and verify the corrected rerun plus tasks 2 and 3.

Corrected outputs:
- Task 1 rerun control: /tmp/aios-m6-t1r-control-final.md
- Task 1 rerun treatment: /tmp/aios-m6-t1r-treatment-final.md
- Task 2 control/treatment: /tmp/aios-m6-t2-control-final.md and
  /tmp/aios-m6-t2-treatment-final.md
- Task 3 control/treatment: /tmp/aios-m6-t3-control-final.md and
  /tmp/aios-m6-t3-treatment-final.md
- Durable SQLite ledger: /tmp/aios-m6-live.db
- Protected repository: /tmp/aios-m6-review at SHA 7797f3ed34f15322d34d296f078cfffc604ef28f

Use this fixed rubric for each output, 0.0 to 1.0 per dimension:
acceptance coverage, evidence accuracy, risk/verification quality, decision
discipline, portability/limitations. Overall is the arithmetic mean. Check
that each corrected pair has its durable task/run/score/pair linkage, shared
protected SHA, matching task/prompt/context hashes, model/effort/tools/budget
parity, passed contamination evidence, and a review reference. Provider
token/cost fields must remain unavailable rather than estimated. Confirm all
six corrected worktrees are clean. Treat the old pair's promote state as a
superseded evidence-integrity finding, not as valid support for M6.

Return self-contained Markdown containing:
- per-task control/treatment dimension scores and rationales;
- aggregate means and treatment-minus-control delta;
- corrected-ledger verification and contamination/parity results;
- P0/P1/P2/P3 findings, including any remaining old-pair evidence issue;
- bounded promote/revise/defer decision for M6 and minimum next gate.

The claim is only about this three-task audit corpus. Do not claim general
productivity, satellite readiness, or production safety.
