# Module: Make Interfaces Feel Better

Module ID: `@module:make_interfaces_feel_better`

## Purpose

Bring the vendored `make-interfaces-feel-better` skill into the TMCP visual-polish path as a detail-level UI quality pass.

## Source

- Skill source: `skills/make-interfaces-feel-better/SKILL.md`
- Reference files: `typography.md`, `surfaces.md`, `animations.md`, and `performance.md` in the same skill directory.

## Use When

- A UI needs polish after the layout, product archetype, and surface hierarchy are broadly correct.
- A generated component feels close but still slightly off.
- A review needs concrete implementation-level fixes for typography, surfaces, motion, or interaction states.

## Rules

- Preserve the host project's design system, accessibility requirements, and product-specific visual identity.
- Use concentric border radius: outer radius equals inner radius plus padding.
- Prefer optical alignment when icons, asymmetric shapes, or text baselines look geometrically centered but visually wrong.
- Use layered shadows and subtle outlines intentionally; do not add heavy decorative depth to dense product UI.
- Keep interactive transitions interruptible and property-specific. Never use `transition: all`.
- Use `tabular-nums` for changing numeric values.
- Use `text-wrap: balance` for headings and `text-wrap: pretty` for readable body copy where supported.
- Add subtle image outlines with pure black or pure white opacity, not tinted neutrals.
- Use `scale(0.96)` for button press feedback when motion is appropriate.
- Reserve `will-change` for observed transform, opacity, or filter stutter.
- Keep interactive hit areas at least 40 by 40 pixels without overlapping adjacent controls.

## Review Output

When reviewing UI changes, group findings by principle and use markdown tables with `Before` and `After` columns. Omit empty principle sections.

## Exit

Exit after translating the relevant detail-polish rules into concrete edits or findings. Do not duplicate the full source skill into the TMCP packet unless the user explicitly asks for the full reference.
