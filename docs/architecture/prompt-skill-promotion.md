# Prompt and Skill Promotion

AIOS promotion gates prevent a prompt, skill, judge, or workflow pattern from becoming active because one run looked promising.

Lifecycle:

```text
draft -> candidate -> tested -> approved -> active -> deprecated
```

Promotion beyond `candidate` requires evidence such as:

- user approval
- passing tests
- repeated successful use
- better judge scores with rationale
- reduced rework
- lower cost
- fewer automation failures
- improved project health
- successful downstream implementation

`promotion_lifecycle_items` stores item kind, key, source run, status, evidence, and status reason. A status is not authoritative without its evidence and reason.
