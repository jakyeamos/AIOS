# Module: Data Realism Polish

Module ID: `@module:data_realism_polish`

## Purpose

Improve visual credibility by replacing placeholder, perfect, or generic data with plausible product-specific data.

## Use When

- A UI uses demo data, mock records, seed data, empty states, generated examples, dashboards, tables, search results, or AI examples.
- The screen looks polished structurally but still feels fake.

## Rules

- Use realistic entity names, titles, owners, dates, statuses, counts, permissions, source counts, and partial records.
- Mix states. Real operational systems have fresh, aging, stale, blocked, pending, failed, missing, restricted, and incomplete items.
- Use non-round numbers when precision would naturally vary.
- Avoid suspicious perfection: 100 percent completion, zero errors, evenly distributed counts, and all-green statuses.
- Avoid generic placeholders such as John Doe, Jane Smith, Acme Corp, Department 1, Sample Document, lorem ipsum, and "Untitled".
- Empty states should teach the next step with one clear primary action and optional examples, not only say that nothing exists.
- Success and error messages should name the object or action, not say only "Success", "Done", "OK", or "Something went wrong".

## Scan Checklist

- Do names, dates, owners, and statuses look plausible for the product domain?
- Are there mixed records and edge cases?
- Do metrics answer a decision question?
- Are permission, source, freshness, or review cues present where trust depends on them?
- Does seed data avoid joke names, placeholder labels, and perfect numbers?

## Output Guidance

When implementing, update only the local example, fixture, seed, story, or mock data needed for the visible surface unless the user asks for a broader data refresh.
