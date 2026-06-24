# Task: Visual Polish

Task ID: `@task:visual_polish`

## Trigger

Use when a request asks to improve, review, or generate UI polish, visual hierarchy, enterprise SaaS presentation, product-screen credibility, dashboard density, AI UI treatment, or realistic seed data.

Also use when a generated screen feels generic, over-decorated, too much like default shadcn output, too card-heavy, or visually inconsistent with the target product.

## Required Modules

- `@module:saas_interaction_architecture`
- `@module:visual_polish_system`
- `@module:enterprise_saas_visual_polish`
- `@module:data_realism_polish`

## Optional Modules

- `@module:make_interfaces_feel_better` when the request needs detail-level UI polish for typography, surfaces, motion, or interaction feel.
- `@module:ai_surface_polish` when the screen contains AI responses, AI editing, citations, generated summaries, suggestions, or review flows.
- `@module:print_report_design` when the output is a fixed-page report, print/PDF artifact, board report, treasurer report, or financial summary.
- `@module:frontend_runtime` when implementation or rendered verification is in scope.
- `@branch:tenure_visual_identity` only when the active project is Tenure or the user explicitly asks for Tenure-specific polish.
- `@branch:bidcamp_visual_identity` only when the active project is BidCamp or the user explicitly asks for BidCamp-specific polish.
- `@branch:framework_labs_editorial_identity` only when the active project is Framework Labs or the user explicitly asks for Framework Labs-specific design.

## Traversal Contract

- LOAD this task for visual polish work even when the user did not ask for code changes.
- USE `@module:saas_interaction_architecture` before visual styling whenever container choice, overlay behavior, table/form mechanics, loading state, empty state, toast behavior, or AI interaction structure is relevant.
- CONSIDER `@module:make_interfaces_feel_better` when the request mentions feel, polish details, typography, hover states, animation, spacing, shadows, borders, radius, or interaction quality.
- CONSIDER `@module:ai_surface_polish` only when AI affordances or AI-generated output appear in the UI.
- CONSIDER `@module:print_report_design` when the target artifact is an HTML-to-PDF report, board packet, printable report, financial dashboard, treasurer report, or fixed-page executive artifact.
- CONSIDER `@branch:tenure_visual_identity` only after confirming the project-specific Tenure identity is relevant.
- CONSIDER `@branch:bidcamp_visual_identity` only after confirming the product is BidCamp or a bid-operations surface using that source identity.
- CONSIDER `@branch:framework_labs_editorial_identity` only after confirming the product is Framework Labs or a publication-style software research lab surface using that source identity.
- SKIP product-specific branches when producing a portable boilerplate polish pass.
- USE `@module:frontend_runtime` for rendered verification when files change or screenshots are needed.

## Instructions

1. Identify the screen archetype, primary user task, primary object, primary action, and output form factor.
2. Resolve container and interaction architecture before visual treatment.
3. Select the density tier needed for the work surface: comfortable, standard, or compact.
4. Review surface hierarchy before color or decoration: canvas, panel, card, overlay.
5. If detail-level feel is in scope, use the `make_interfaces_feel_better` module for checks such as border radius math, optical alignment, shadows, micro-interactions, font smoothing, tabular numbers, image outlines, transition specificity, and hit areas.
6. If fixed-page report or PDF output is in scope, use `print_report_design` and verify against the exported artifact, not only the browser view.
7. Check for default-component artifacts: card quilts, excessive radius, heavy shadows, raw color utilities, decorative gradients, and placeholder data.
8. Tighten typography, alignment, spacing, state treatment, and data realism before adding visual effects.
9. If implementation is requested, edit the smallest set of UI files and preserve existing design-system conventions.
10. If review is requested, return prioritized findings with concrete fixes and cite the relevant file or screen region when available.

## Output Contract

Return:

- selected archetype and density tier
- loaded modules and skipped optional nodes with reasons
- interaction architecture or print-report constraints applied, if any
- prioritized polish findings or edits
- forbidden/default visual patterns found
- realistic-data gaps
- AI surface risks, if applicable
- verification performed or still needed

## Exit

Exit after the smallest sufficient polish packet is assembled. Do not load product-specific visual identity branches for a generic boilerplate polish pass.
