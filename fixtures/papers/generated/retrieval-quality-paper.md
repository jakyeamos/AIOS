# Retrieval Quality In Local Agent Systems

## Abstract

This paper argues that local agent systems improve when retrieval quality is evaluated as an operational constraint rather than an interface feature. The analysis describes three recurring failure modes: stale context, irrelevant context, and context that is plausible but not source-backed.

## Introduction

Agent workflows depend on context selection. When retrieval is noisy, downstream reasoning becomes expensive and brittle. A system can appear helpful while still using material that does not answer the current task.

## Method

The proposed method compares baseline and candidate retrieval packets across repeated implementation tasks. Each packet is scored for source relevance, freshness, contradiction risk, and compactness.

## Discussion

The main result is that compact source-backed packets outperform broad recall when the task requires code changes. The tradeoff is that compact packets require better omission traces so operators can inspect what was excluded.

## Conclusion

Retrieval quality should be measured through task outcomes and source auditability, not only through similarity scores.

## References

[1] Synthetic fixture for AIOS humanizer experiments.
