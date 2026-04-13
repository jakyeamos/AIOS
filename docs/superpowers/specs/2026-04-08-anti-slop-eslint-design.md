# Anti-Slop ESLint — Design Spec

**Date:** 2026-04-08
**Status:** Proposed
**Author:** jakyeamos
**Target:** Multi-project TypeScript/React repos

---

## Executive Summary

Most projects already have TypeScript or baseline ESLint, but that still leaves a class of regressions untouched: unnecessary `"use client"`, placeholder copy, demo-data-first pages, empty states with no action, and labels that sound like generic template output instead of product-specific language.

The fix is an ESLint 9 flat-config plugin with a narrow goal: catch high-confidence slop before it lands. The plugin should enforce structural quality, not taste. It should block obvious boilerplate and cargo-cult patterns, not attempt to score aesthetics.

---

## Problem

Many repos effectively use lint for syntax and types only:

```json
"lint": "tsc --noEmit"
```

That protects type soundness, but it does not protect product quality. The current failure modes are different:

- Server-first Next.js architecture can drift toward unnecessary client components
- UI copy can regress toward generic dashboard language instead of the product's own vocabulary
- Placeholder states can ship because they are valid JSX and valid TypeScript
- Demo or seeded data can quietly become the primary source for a production page
- Empty states can explain the problem but offer no next action
- React cargo-cult patterns like `useMemo` can spread without evidence they are needed

These are not runtime crashes. They are quality regressions. TypeScript will not catch them.

---

## Definition of Slop

For this system, "slop" means one of five things:

1. **Placeholder product language**: `"Coming soon"`, `"TBD"`, `"Lorem ipsum"`, or equivalent filler
2. **Generic SaaS copy**: labels or descriptions that could belong to any dashboard and do not reflect the product's own concepts
3. **Structural boilerplate**: pages that render chrome and demo panels without a real data claim or decision path
4. **Framework cargo culting**: `"use client"`, `useMemo`, and `useCallback` used by habit instead of necessity
5. **Actionless UI**: empty, error, or sparse states that describe a gap but do not tell the operator what to do next

The lint rules should target these precisely. Anything fuzzier belongs in human review.

---

## Goals

- Add a reusable anti-slop ESLint layer without introducing a second style system
- Encode a small set of high-signal anti-slop rules as configurable project rules
- Keep false positives low enough that disables are rare and explicit
- Make `npm run lint` meaningful for both code quality and product quality
- Support gradual rollout: warn first, then promote stable rules to error

## Non-Goals

- Replacing design review
- Enforcing visual taste or layout composition from AST alone
- Linting Python, Markdown, or Vault files
- Blocking all generic words in all contexts

---

## Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| ESLint format | Flat config (`eslint.config.mjs`) | Matches ESLint 9 and current Next.js direction |
| Base config | `eslint-config-next/core-web-vitals` | Reuse framework defaults instead of rebuilding them |
| Plugin packaging | Reusable plugin with per-project config | Core rules stay portable; vocabulary stays local |
| Scope | `app/**/*.ts(x)`, `components/**/*.ts(x)`, `lib/**/*.ts(x)` by default | Focus on UI surfaces where slop appears |
| Rollout | `warn` first, later selective `error` | Avoid immediate rule backlash |
| Exceptions | Inline disable with required explanation | Makes waivers visible and costly |
| CSS handling | Out of scope for v1 | ESLint is the wrong first tool for `globals.css` semantics |

---

## Integration Plan

### Package changes

Add an ESLint config file and update scripts:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "lint": "eslint . && tsc --noEmit"
  }
}
```

### File layout

```text
repo/
  eslint.config.mjs
  eslint/
    anti-slop/
      index.mjs
      presets/
        react-next.mjs
      rules/
        no-unjustified-use-client.mjs
        no-useless-memo.mjs
        no-placeholder-copy.mjs
        no-marketing-copy.mjs
        require-empty-state-action.mjs
        no-demo-data-primary-path.mjs
        no-generic-stat-label.mjs
      tests/
        no-unjustified-use-client.test.mjs
        no-useless-memo.test.mjs
        no-placeholder-copy.test.mjs
        no-marketing-copy.test.mjs
        require-empty-state-action.test.mjs
        no-demo-data-primary-path.test.mjs
        no-generic-stat-label.test.mjs
  .config/
    anti-slop.json
```

### Config shape

```javascript
// eslint.config.mjs
import nextVitals from "eslint-config-next/core-web-vitals";
import antiSlop from "./eslint/anti-slop/index.mjs";
import antiSlopConfig from "./.config/anti-slop.json";

export default [
  ...nextVitals,
  {
    files: ["app/**/*.{ts,tsx}", "components/**/*.{ts,tsx}", "lib/**/*.{ts,tsx}"],
    plugins: {
      "anti-slop": antiSlop,
    },
    settings: {
      "anti-slop": antiSlopConfig,
    },
    rules: {
      "anti-slop/no-unjustified-use-client": "error",
      "anti-slop/no-useless-memo": "warn",
      "anti-slop/no-placeholder-copy": "error",
      "anti-slop/no-marketing-copy": "warn",
      "anti-slop/require-empty-state-action": "warn",
      "anti-slop/no-demo-data-primary-path": "error",
      "anti-slop/no-generic-stat-label": "warn",
    },
  },
];
```

---

## Rule Set v1

### 1. `anti-slop/no-unjustified-use-client`

**Intent:** Prevent Server Components from drifting into client components unless the file clearly needs it.

**Report when:**
- File begins with `"use client"`
- File has no state/effect hooks
- File has no event handlers in JSX
- File does not reference browser-only globals
- File does not import known client-only libraries

**Allowed examples:**
- Chart wrappers that need browser rendering
- Providers with client state
- Interactive filters, editors, drag/drop, keyboard handlers

**Autofix:** remove `"use client"` when the rule is certain

This rule directly enforces a common React/Next default: keep components server-first unless the file clearly needs the client.

### 2. `anti-slop/no-useless-memo`

**Intent:** Stop prophylactic `useMemo` and `useCallback`.

**Report when:**
- `useMemo` wraps a trivial map/filter/sort on a small local array
- `useMemo` returns a primitive or string concatenation
- `useCallback` is used only to pass a handler one level down without memo-sensitive children

**Do not report when:**
- The hook stabilizes a value passed into a memoized third-party chart or virtualized list
- The work is obviously expensive
- The file includes an inline justification comment above the hook

This rule stays `warn` until real false-positive data is available.

### 3. `anti-slop/no-placeholder-copy`

**Intent:** Block obvious filler text from shipping.

**Initial banned patterns:**
- `coming soon`
- `todo`
- `tbd`
- `lorem ipsum`
- `placeholder`
- `sample data`
- `dummy data`

**Checked nodes:**
- `JSXText`
- string literals
- template literals
- `metadata.title` and `metadata.description`

This rule is high confidence and should be `error` from the start.

### 4. `anti-slop/no-marketing-copy`

**Intent:** Catch generic AI/SaaS language that weakens the product's own voice.

**Initial banned terms:**
- `powerful`
- `seamless`
- `unlock`
- `supercharge`
- `transform your workflow`
- `next-generation`
- `analytics dashboard`

**Important constraint:** the rule should only scan user-facing strings, not variable names, comments, or technical docs.

This is a `warn` rule because wording has more edge cases than placeholder detection.

### 5. `anti-slop/require-empty-state-action`

**Intent:** Empty states must tell the operator what to do next.

**Report when:**
- A JSX subtree contains patterns like `No runs`, `No prompts`, `Nothing found`, `0 results`
- The same subtree contains no actionable control
- No next-step verb is present, such as `Retry`, `Open`, `Create`, `Seed`, `Run`, `Adjust filter`

**Pass examples:**
- "No prompts matched this filter. Clear filters or open the latest session."
- "No active runs. Start a new workflow run or inspect the last completed session."

This rule encodes the UI thesis that every screen should lead to a decision.

### 6. `anti-slop/no-demo-data-primary-path`

**Intent:** Stop a route from quietly becoming a demo page.

**Report when:**
- A route or top-level screen imports from project-configured demo data sources
- The screen does not call a project-configured real data source or loader
- The screen renders demo data as primary content

**Allowed case:**
- Demo data is used only for fallback cards, stories, previews, or sparse panels while the screen also loads real data

This rule must be driven by project configuration. Example config can mark imports like `@/lib/seed`, `fixtures/*`, `mocks/*`, or `demo/*` as demo-data modules.

### 7. `anti-slop/no-generic-stat-label`

**Intent:** Keep metrics tied to product concepts instead of generic SaaS nouns.

**Initial banned labels:**
- `Performance`
- `Insights`
- `Overview`
- `Analytics`
- `Usage`
- `Activity`

**Checked locations:**
- `label` prop on `StatCard`
- chart titles
- section headings shorter than three words

**Allowed labels:**
- `Open Sessions`
- `Failed Imports`
- `Prompt Reuse Rate`
- `Queued Jobs`
- `Orders Pending Review`

This rule should be configuration-driven so the lexicon can evolve without changing rule logic.

---

## Lexicon Strategy

Keep all banned and allowed phrase sets in one config file:

```json
{
  "placeholderPatterns": ["coming soon", "todo", "tbd", "lorem ipsum"],
  "marketingPatterns": ["powerful", "seamless", "supercharge"],
  "genericStatLabels": ["Performance", "Insights", "Overview", "Analytics"],
  "actionWords": ["retry", "open", "create", "run", "fix", "clear filter"],
  "demoDataModules": ["@/lib/seed", "@/demo", "@/mocks", "@/fixtures"],
  "realDataIndicators": ["getCaller", "fetch", "db", "prisma", "trpc"]
}
```

Rules should read from config rather than hard-coding phrases in multiple places. This keeps the core plugin reusable and lets each repo define its own vocabulary.

---

## How Each Rule Should Work

| Rule | Technique | Confidence |
|---|---|---|
| `no-unjustified-use-client` | file-level AST scan + import analysis + JSX event scan | high |
| `no-useless-memo` | hook call analysis | medium |
| `no-placeholder-copy` | string literal and JSX text matching | high |
| `no-marketing-copy` | user-facing string matching | medium |
| `require-empty-state-action` | subtree text scan + action element detection | medium-high |
| `no-demo-data-primary-path` | import graph + route file heuristic | high |
| `no-generic-stat-label` | prop/value matching | medium-high |

The first release should favor rules with deterministic AST signals over ambitious heuristics.

---

## Testing Strategy

Each rule gets `RuleTester` coverage with:

- 3 to 5 valid examples
- 3 to 5 invalid examples
- at least one real project-inspired fixture
- one explicit false-positive regression test when discovered

Minimum acceptance bar before promotion from `warn` to `error`:

- zero known false positives in current codebase
- at least two true positives found during initial cleanup
- at least one regression test covering the discovered pattern

---

## Rollout Plan

### Phase 1: Real lint baseline

1. Add `eslint.config.mjs`
2. Switch `npm run lint` to `eslint . && tsc --noEmit`
3. Enable Next.js defaults only
4. Fix baseline issues until clean

### Phase 2: High-confidence anti-slop rules

1. Add `no-unjustified-use-client`
2. Add `no-placeholder-copy`
3. Add `no-demo-data-primary-path`
4. Run across the first target repo
5. Fix violations before merge

### Phase 3: Medium-confidence guidance rules

1. Add `require-empty-state-action`
2. Add `no-generic-stat-label`
3. Add `no-marketing-copy`
4. Start as warnings only

### Phase 4: React cargo-cult cleanup

1. Add `no-useless-memo`
2. Tune against real chart and editor cases
3. Keep as warning until repeated clean runs prove it is stable

---

## Failure Policy

Rules should not be disabled casually.

Allowed disable format:

```tsx
// eslint-disable-next-line anti-slop/no-generic-stat-label -- "Activity" is correct here because it mirrors the upstream table name
```

Any disable without a reason should fail lint once the plugin supports comment validation. That can be a v2 rule if needed.

---

## Success Metrics

After adoption, the following should trend down:

- count of `"use client"` files
- count of demo-data-first route surfaces
- count of placeholder strings in shipped UI
- count of generic metric labels
- count of lint disables for anti-slop rules

This is a quality system, not just a static check. The rule set is working if it changes what gets written.

---

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Rules feel subjective | Team ignores them | Start with deterministic rules only |
| Too many warnings | Lint becomes background noise | Promote only proven rules; delete weak ones |
| Overfitting to current copy | Future UI work feels constrained | Keep lexicon centralized and easy to edit |
| ESLint used for layout judgment | False positives spike | Keep visual composition out of v1 |

---

## Implementation Order

1. Add ESLint flat config to the first target repo
2. Update `npm run lint`
3. Implement `no-unjustified-use-client`
4. Implement `no-placeholder-copy`
5. Implement `no-demo-data-primary-path`
6. Clean current violations
7. Add warning-level rules
8. Add tests for every discovered regression

---

## Recommendation

Build this as a reusable core plugin with per-project adapters. The value comes from separating stable anti-slop mechanics from project vocabulary. The core should stay small and portable; each repo should supply its own lexicon, demo-data markers, and domain labels.
