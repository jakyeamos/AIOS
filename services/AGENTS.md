# AIOS Services Agent Router

This directory contains Python control-plane services for AIOS.

Before non-trivial service work:

1. Read `../.agents/context/README.md`.
2. Read `../.agents/context/python.md`.
3. Read `.context/README.md` if the touched area is listed there.

## Local Rules

- Keep reusable logic in `services/`; keep CLI orchestration in `bin/`.
- Do not import `bin/` from `services/`.
- Use explicit return types and stable data shapes for public helpers.
- Run focused pytest files plus Ruff/BasedPyright for touched Python code.
