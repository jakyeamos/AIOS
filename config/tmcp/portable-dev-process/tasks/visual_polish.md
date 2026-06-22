# Task: Visual Polish

Task ID: `@task:visual_polish`

## Trigger

Use when a request asks to improve, review, or generate UI polish, visual hierarchy, enterprise SaaS presentation, product-screen credibility, dashboard density, AI UI treatment, or realistic seed data.

Also use when a generated screen feels generic, over-decorated, too much like default shadcn output, too card-heavy, or visually inconsistent with the target product.

## Required Modules

- `@module:visual_polish_system`
- `@module:make_interfaces_feel_better`
- `@module:enterprise_saas_visual_polish`
- `@module:data_realism_polish`

## Optional Modules

- `@module:ai_surface_polish` when the screen contains AI responses, AI editing, citations, generated summaries, suggestions, or review flows.
- `@module:frontend_runtime` when implementation or rendered verification is in scope.
- `@branch:tenure_visual_identity` only when the active project is Tenure or the user explicitly asks for Tenure-specific polish.

## Traversal Contract

- LOAD this task for visual polish work even when the user did not ask for code changes.
- CONSIDER `@module:ai_surface_polish` only when AI affordances or AI-generated output appear in the UI.
- CONSIDER `@branch:tenure_visual_identity` only after confirming the project-specific Tenure identity is relevant.
- SKIP product-specific branches when producing a portable boilerplate polish pass.
- USE `@module:frontend_runtime` for rendered verification when files change or screenshots are needed.

## Instructions

1. Identify the screen archetype, primary user task, primary object, and primary action.
2. Select the density tier needed for the work surface: comfortable, standard, or compact.
3. Review surface hierarchy before color or decoration: canvas, panel, card, overlay.
4. Apply the `make_interfaces_feel_better` module for detail-level checks: border radius math, optical alignment, shadows, micro-interactions, font smoothing, tabular numbers, image outlines, transition specificity, and hit areas.
5. Check for default-component artifacts: card quilts, excessive radius, heavy shadows, raw color utilities, decorative gradients, and placeholder data.
6. Tighten typography, alignment, spacing, state treatment, and data realism before adding visual effects.
7. If implementation is requested, edit the smallest set of UI files and preserve existing design-system conventions.
8. If review is requested, return prioritized findings with concrete fixes and cite the relevant file or screen region when available.

## Output Contract

Return:

- selected archetype and density tier
- loaded modules and skipped optional nodes with reasons
- prioritized polish findings or edits
- forbidden/default visual patterns found
- realistic-data gaps
- AI surface risks, if applicable
- verification performed or still needed

## Exit

Exit after the smallest sufficient polish packet is assembled. Do not load project-specific visual identity branches for a generic boilerplate polish pass.
