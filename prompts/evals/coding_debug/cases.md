## Case 1: Runtime type error

**Inputs:**
- symptom: TypeError reading property from undefined
- context: stack trace + target file excerpt

**Expected output shape:**
- Root cause
- Minimal fix
- Verification steps

**Pass criteria:**
- [ ] Root cause is explicit and evidenced
- [ ] Fix scope is minimal

**Last run:** 2026-04-23 | **Result:** pass | **Notes:** Seed case

## Case 2: Explicit false must survive a default

**Inputs:**
- symptom: `isEnabled(false)` returns true
- context: `const isEnabled = v => v || true`

**Expected output shape:**
- Observation and boolean-truthiness cause
- Minimal `v ?? true` fix
- False, true, and absent-input verification

**Pass criteria:**
- [ ] Does not replace explicit false with the default
- [ ] Does not claim the verification ran when it was only specified

**Last run:** not run | **Result:** pending | **Notes:** Added for v1.1 forward testing
