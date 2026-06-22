# Module: AI Surface Polish

Module ID: `@module:ai_surface_polish`

## Purpose

Make AI UI feel source-aware, reversible, reviewable, and integrated into the product workflow rather than bolted on.

## Use When

- A screen includes AI summaries, generated responses, AI-assisted editing, suggestions, citations, source panels, agent activity, or review states.
- The task asks to make an AI feature feel more trustworthy or less generic.

## Rules

- AI should be inline where the user is working, not isolated in a generic modal by default.
- Label AI output plainly. Use terms like "Generated", "Summary", "Draft", "Sources", and "Needs review".
- Do not let AI output replace underlying evidence. Keep raw results, source lists, or affected content available.
- Show source count, source access, source freshness, or review state when trust depends on them.
- For AI edits to existing content, use suggestion or diff treatment with accept, reject, revise, and revert paths.
- Require visible human review before publishing material AI-generated changes when the workflow is consequential.
- Use calm uncertainty language. Avoid fake confidence percentages, magic claims, sparkle branding, and "ask anything" copy as a primary trust signal.
- Keep AI visual treatment restrained: a subtle lane, border, label, or source panel is usually enough.

## Scan Checklist

- Is the AI output labeled?
- Are sources or evidence visible?
- Can the user inspect what changed?
- Can the user accept, reject, revise, or revert?
- Is uncertainty or source conflict handled without alarmism?
- Does the AI affordance support the workflow instead of competing with it?

## Output Guidance

Flag any silent overwrite path, unsourced AI answer, standalone generic AI modal, or decorative AI branding as a high-priority polish issue.
