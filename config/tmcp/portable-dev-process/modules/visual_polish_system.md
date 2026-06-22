# Module: Visual Polish System

Module ID: `@module:visual_polish_system`

## Purpose

Provide a portable visual-quality pass for product UI. This module is product-neutral: it improves hierarchy, density, surface logic, typography, spacing, states, and credibility without hardcoding a specific brand.

## Use When

- A UI needs polish beyond functional correctness.
- A generated screen looks generic, decorative, sparse, or visually incoherent.
- A product surface needs a professional SaaS or internal-tool finish.
- A design review needs actionable implementation guidance.

## Rules

- Start from information architecture: primary task, primary object, primary action, dominant region, and supporting region.
- Use surface hierarchy before decorative styling. Prefer canvas, panel, card, and overlay roles with clear boundaries.
- Do not make every section a card. Use cards for repeated items, modals, and genuinely framed tools.
- Use borders, dividers, tint, and spacing before shadows.
- Reserve shadows for overlays, menus, popovers, dialogs, and sheets.
- Keep radii tight to medium. Avoid large pill-like product chrome unless it is a badge, avatar, or compact pill.
- Use color sparingly for meaning: selected state, primary action, focus, status, or important linked entity.
- Avoid one-note palettes, decorative gradients, glass effects, glow, bokeh, and trend-led AI styling.
- Match type scale to container scale. Dense panels, tables, sidebars, and toolbars need smaller controlled headings.
- Keep letter spacing neutral unless the host design system explicitly defines otherwise.
- Use tabular numerals for counts, dates, percentages, durations, and IDs when supported by the stack.
- Preserve layout dimensions for loading, empty, and error states so the screen does not jump.

## Scan Checklist

- Is the primary task visually obvious?
- Is one region dominant, or are all cards competing equally?
- Are surfaces nested without a reason?
- Are there raw color utilities, decorative gradients, or heavy shadows in product UI?
- Are empty, loading, partial, success, and error states present where the flow needs them?
- Does text fit without overlap at desktop and mobile widths?
- Are controls sized consistently and aligned to a stable rhythm?
- Do hover, selected, disabled, and focus states communicate function rather than decoration?

## Output Guidance

When reviewing, lead with the highest-impact visual issue, then list concrete changes. When implementing, change layout and token usage before adding any new component abstraction.
