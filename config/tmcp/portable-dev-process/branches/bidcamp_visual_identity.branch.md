# Branch: BidCamp Visual Identity

Branch ID: `@branch:bidcamp_visual_identity`

## Use Only When

- The active product is BidCamp.
- The user explicitly asks for BidCamp-specific design.
- A supplied source packet identifies the screen as a bid, opportunity, procurement, worklist, or pursuit-management product using the BidCamp design brief.

## Skip When

- The request asks for generic SaaS polish.
- The host product is not bid, procurement, pursuit, or opportunity management.
- The task needs only interaction architecture or accessibility behavior without product-specific visual identity.

## Source

Derived from the user-supplied `DESIGN-BRIEF.html` BidCamp design brief.

## Direction

BidCamp should feel like a focused bid-operations workspace: calm, slightly warm, dense enough for daily work, and organized around today's bid actions, stage movement, and deal context.

## Visual System

- Use a soft near-white operational canvas, white cards or panels, subtle cool borders, and a restrained blue primary accent.
- Use rounded but controlled panel geometry. Avoid sharp editorial identity, large playful radius, heavy shadows, and decorative gradients.
- Use Plus Jakarta Sans or the host sans for functional UI and Bricolage Grotesque-like display moments when the local stack supports it.
- Keep letter spacing close to neutral. Use mono only for compact token names, IDs, or measurement-like metadata.
- Preserve status chips, tag palettes, and small semantic markers as operational signals, not decoration.

## Screen Patterns

- Use a flowband or KPI strip for the current pipeline slice instead of disconnected metric cards when metrics are peers.
- Use a today's-worklist pattern for actionable bids, stale replies, due dates, next steps, and owner attention.
- Use list or table-first pages with clear row signals, stage chips, deadlines, owners, and right-side actions.
- Use slide-in detail panels for bid context that benefits from keeping the list visible.
- For per-page playbooks, keep the primary object and next action visible: opportunity, stage, deadline, owner, response state, and context notes.

## Data Realism

- Use plausible bid records, agencies, due dates, stages, owners, reply states, and stale or hot signals.
- Mix states such as new, needs reply, stale, hot, won, lost, pending, and missing context.
- Avoid generic CRM examples, perfect pipeline counts, and placeholder company/person names.

## Output Guidance

When this branch is selected, include the BidCamp-specific operational pattern being used. If the task is not a bid-operations surface, record this branch as considered and skipped.
