# Citation Fidelity In Generated Research Drafts

## Abstract

This paper examines citation fidelity in AI-generated research drafts. It focuses on whether claims remain attached to available evidence after summarization, rewriting, and style editing.

## Introduction

Generated drafts often sound complete before their citation trail is complete. This creates a failure mode where polished prose hides weak evidence coverage.

## Method

The evaluation uses controlled draft fixtures with explicit citation markers. A humanizer pass is considered successful only when it improves readability while preserving citation markers, claim boundaries, and uncertainty language.

## Discussion

The strongest humanizer behavior is conservative. It improves transitions and sentence rhythm without adding unsupported claims or converting qualified statements into certain ones.

## Conclusion

Citation fidelity requires explicit validation after style transformation. A rewrite that reads better but drops citation markers should fail the workflow.

## References

[1] Synthetic fixture for AIOS humanizer experiments.
