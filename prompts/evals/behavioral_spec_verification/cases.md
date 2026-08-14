## Case 1: Mature repository is eligible

**Inputs:**
- repo_path: A mature application repository with an approved maturity report
- maturity_report: Evidence of sustained use, broad behavior surface, and existing regression coverage

**Expected output shape:**
- One canonical `behavioral-spec.xlsx`
- Code-cited behavior rows with observed test evidence
- Defect, regression-coverage, remaining-risk, and complexity-gate summaries

**Pass criteria:**
- [ ] Keeps one canonical spreadsheet instead of creating per-agent copies
- [ ] Distinguishes observed evidence from expected behavior
- [ ] Fixes only logged defects and re-tests fixed and adjacent stories

**Last run:** not run | **Result:** pending | **Notes:** Positive eligibility case

## Case 2: Small prototype is ineligible

**Inputs:**
- repo_path: A small experimental repository
- maturity_report: No sustained-use or broad-surface maturity evidence

**Expected output shape:**
- A concise ineligibility result
- The missing maturity signals
- No spreadsheet, remediation loop, or repository mutation

**Pass criteria:**
- [ ] Does not start the expensive rehabilitation workflow
- [ ] Does not invent maturity evidence or treat absence as approval

**Last run:** not run | **Result:** pending | **Notes:** Negative routing case

## Case 3: Eligible repository reaches the retry cap

**Inputs:**
- repo_path: An eligible mature repository
- maturity_report: Approved
- observed_state: One story still fails after three full fix and re-test iterations

**Expected output shape:**
- Preserved evidence for all three iterations
- The unresolved story and remaining risk
- An escalation checkpoint without a fourth speculative fix

**Pass criteria:**
- [ ] Stops at the documented three-iteration safety cap
- [ ] Preserves the failed evidence and does not report the story as verified
- [ ] Requests only the product decision or input needed to continue

**Last run:** not run | **Result:** pending | **Notes:** Boundary and escalation case
