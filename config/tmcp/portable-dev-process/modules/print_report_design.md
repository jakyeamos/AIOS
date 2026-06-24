# Module: Print Report Design

Module ID: `@module:print_report_design`

## Purpose

Add design and rendering rules for compact board reports, financial summaries, and HTML-to-PDF artifacts where print fidelity and decision speed matter.

## Source

Derived from the user-supplied `Treasurers_Report_Design_Bible.docx`.

## Use When

- The task involves a PDF, printable report, board packet, treasurer report, financial dashboard, executive summary, or HTML rendered through headless Chrome.
- A product surface must be read as a fixed page rather than an infinite app screen.
- Financial or operational metrics need board-ready hierarchy, number formatting, and chart selection.

## Rules

- Give each page one job. For monthly board financials, page one should be an at-a-glance exception dashboard with five to seven clusters, while page two carries supporting ledgers or detail.
- Put the headline decision number top-left and make it the largest, highest-contrast value. Position and hierarchy should reinforce each other.
- Separate restricted and unrestricted money everywhere it matters. Compute runway from spendable or unrestricted funds only, not total cash.
- Use tabular lining figures for all numbers in KPI cards, tables, chart labels, and financial summaries. Right-align numeric columns.
- Format financial values with thousands separators, negatives in parentheses, zeros as muted em dashes, whole dollars for board summaries, and currency symbols only where they reduce ambiguity.
- Do not encode meaning with color alone. Pair favorable or unfavorable state with sign, position, glyph, label, or wording so the report survives grayscale.
- Prefer tables, line charts, horizontal bars, stacked bars, and bullet graphs. Avoid pies, gauges, 3D charts, red/green-only semantics, decorative grids, and charts for single values.
- Use SVG charts for PDF output. Canvas charts often rasterize poorly in generated PDFs.
- Use physical page constraints for print artifacts: explicit page size, margins, fixed report width, page breaks, and print-safe spacing. Avoid viewport units for print layout.
- For headless Chrome PDF generation, wait for fonts and network idle before printing, and enable print backgrounds plus exact color adjustment so tints, bars, and rules survive.
- Self-host report fonts where numeric alignment matters. Remote font substitution can silently break tabular alignment.

## Scan Checklist

- Can the target reader understand the headline position, runway, and material exceptions in under a minute?
- Are the primary metric formulas explicit and reused consistently?
- Are restricted funds, source notes, freshness dates, and assumptions visible enough to prevent misreading?
- Does the generated PDF preserve fonts, colors, charts, margins, page breaks, and table alignment?
- Are charts earning their space, or would a number, table, or short narrative be clearer?

## Output Guidance

When implementing, verify the actual exported PDF or printed artifact, not only the browser view. Report failures as print fidelity issues when fonts, backgrounds, chart sharpness, page breaks, or numeric alignment differ between screen and PDF.
