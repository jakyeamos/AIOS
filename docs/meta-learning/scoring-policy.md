# Meta-Learning Scoring Policy

Scoring estimates whether a detected signal is worth a reviewable proposal. It does not grant permission to apply the proposal.

## Base Weights

- Explicit always/never/from-now-on correction: +5
- Repeated correction across sessions: +4
- Repeated correction within one session: +3
- Single correction: +2
- Repeated approval: +2
- Single approval: +1
- Repeated manual command: +3
- Repeated tool loop/failure: +3
- Repeated model mismatch: +3
- Repeated context miss: +4

## Modifiers

- Recent signal: +1
- Explicit remember/from-now-on request: +2
- Multi-project evidence: +2
- Contradiction: conflict, no auto-promotion
- High blast radius, security-sensitive, or permission-risk signal: manual review required

## Confidence Bands

- 0-2: observe only
- 3-4: suggest project note or low-risk command
- 5-7: propose project rule, skill, or command
- 8+: strong review-gated proposal

## Quality Filter

Signals must pass four questions:

- Is it specific and actionable?
- Does it have future value?
- Is it supported and non-contradictory?
- Is it safe to route?

The filter rejects generic best practices, vague one-off preferences, contradictory signals without enough evidence, and unsafe permission changes.
