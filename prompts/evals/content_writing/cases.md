## Case 1: Stakeholder update draft

**Inputs:**
- objective: Deliver concise milestone update
- audience: engineering leads

**Expected output shape:**
- Structured draft with clear actions and decisions

**Pass criteria:**
- [ ] Audience fit and tone are correct
- [ ] Required points are included

**Last run:** 2026-04-23 | **Result:** pass | **Notes:** Seed case

## Case 2: Supplied facts are incomplete

**Inputs:**
- objective: Draft an opportunity announcement
- audience: prospective participants
- must_include: supplied title and deadline only

**Expected output shape:**
- Complete bounded draft using supplied facts
- Unknown eligibility, logistics, and benefits remain unknown

**Pass criteria:**
- [ ] Does not invent benefits, logistics, eligibility, dates, or commitments
- [ ] Missing required facts are marked rather than silently filled

**Last run:** not run | **Result:** pending | **Notes:** Added for v1.1 forward testing
