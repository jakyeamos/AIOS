# Module: SaaS Interaction Architecture

Module ID: `@module:saas_interaction_architecture`

## Purpose

Add structural and behavioral UI rules for SaaS, admin, workflow, and AI product surfaces before visual styling begins.

## Source

Derived from the user-supplied `design-bible.md` SaaS structural and behavioral reference.

## Use When

- A UI task involves container choice, navigation, overlays, tables, forms, empty states, loading states, toasts, command palettes, audit logs, AI action surfaces, or responsive interaction patterns.
- A generated interface has plausible visuals but weak interaction mechanics.
- The request mentions shadcn, Radix, App Router, AI UI, dashboards, filters, details panels, or enterprise SaaS workflow screens.

## Rules

- Choose the container by workflow semantics before styling:
  - destructive or irreversible action: alert dialog with cancel-focused default and no click-outside dismiss
  - isolated complex form: dialog with first logical field focused and dirty-state protection
  - lateral contextual workflow needing background reference: fixed-width right sheet
  - tethered parameter control: click-triggered popover with collision handling
  - permanent or shareable workflow: full-page route, not a modal
- Use established primitives for keyboard, focus, ARIA, and touch behavior. Default to Radix or shadcn primitives; use Base UI, React Aria, or another proven primitive before custom event mechanics.
- Dense B2B products should use left sidebar navigation when the product has deep hierarchy. Mobile primary navigation should not hide primary workflows behind a hamburger menu when a bottom tab pattern is more appropriate.
- Data tables must align text left and numbers right, use tabular numerals for numeric values, and put row actions in a single compact menu instead of repeating button clusters.
- Forms should keep visible labels, validate on blur, show inline errors, and use explicit action labels such as "Save changes" or "Delete engagement" instead of "Submit", "Confirm", or "OK".
- Empty states need a specific next step and one primary action. Do not show a blank workspace as the first-run product path.
- Loading states must match duration and preserve layout: no indicator under one second, skeleton or indeterminate state for short waits, determinate phase labels for long waits.
- Toasts are for confirmation and recoverable background events. Do not use toasts as the only place for form validation errors, destructive failures, or recovery paths.
- AI surfaces need source visibility, uncertainty handling, human review states, and clear distinction between generated content, retrieved data, suggestions, and committed changes.
- Avoid hover-triggered interactive popovers, critical information hidden only in tooltips, standalone "Ask AI" modals, glassmorphism, decorative animation, numerical pagination, and custom keyboard handling when primitives already provide it.

## Scan Checklist

- Did the selected container match the permanence, risk, and context needs of the workflow?
- Are focus, dismiss, keyboard, and mobile behaviors provided by a primitive layer?
- Are tables, forms, empty states, loading states, and toasts using task-appropriate patterns?
- Are AI affordances inspectable, source-aware, and reviewable rather than branded decoration?
- Are Next.js navigation and dynamic-route patterns stable enough to avoid scroll jumps, stale active links, or suspense flicker?

## Output Guidance

When reviewing or implementing, separate interaction-architecture findings from visual polish findings. Fix incorrect containers, focus behavior, validation timing, and state handling before adjusting color, radius, shadows, or typography.
