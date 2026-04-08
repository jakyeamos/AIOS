#!/usr/bin/env python3
"""
AIOS: rule-artifacts.py
Portable rule artifact model. Read/write JSON artifacts to ~/AIOS/data/rule-artifacts/.

Each artifact is a self-contained description of a promoted rule that can travel
into claude-improvement-lab with all metadata needed to generate tasks and
interpret results.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ARTIFACTS_DIR = Path.home() / "AIOS/data/rule-artifacts"

# Capability taxonomy — maps latent behavior class to a string label.
# Used by generate-rule-bundle.py and for mutation scope selection.
CAPABILITY_CLASSES = {
    "verification",          # checking/validating that output is correct
    "planning",              # structuring approach before acting
    "inspection",            # reading/understanding before modifying
    "completion-validation", # verifying done = actually done
    "incremental-editing",   # making changes in small, reversible steps
    "multi-step-execution",  # coordinating multiple dependent steps
    "claim-calibration",     # not asserting without evidence
    "tool-selection",        # choosing the right tool or approach
}

# Mutation scope by capability class — primary patch type to try first.
CAPABILITY_TO_MUTATION = {
    "verification":          "verification_toggle",
    "planning":              "planning_scaffold",
    "inspection":            "prompt_overlay",
    "completion-validation": "verification_toggle",
    "incremental-editing":   "prompt_overlay",
    "multi-step-execution":  "orchestration_flag",
    "claim-calibration":     "prompt_overlay",
    "tool-selection":        "prompt_overlay",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def infer_capability_class(pattern: dict) -> str:
    """
    Heuristically infer the latent capability class from a pattern row.
    Uses body text keywords + domain. Returns a CAPABILITY_CLASSES member.
    """
    body = (pattern.get("body") or pattern.get("title") or "").lower()
    domain = (pattern.get("domain") or "").lower()

    # Keyword signals — ordered from most specific to least specific
    if any(k in body for k in ("verify output", "verify before", "check output",
                                "confirm output", "validate output", "before finishing")):
        return "completion-validation"
    if any(k in body for k in ("verify", "check that", "assert", "confirm", "validate")):
        return "verification"
    if any(k in body for k in ("plan", "plan your", "outline", "before starting",
                                "think through", "step by step")):
        return "planning"
    if any(k in body for k in ("read before", "inspect", "explore first", "understand before",
                                "look at", "check existing")):
        return "inspection"
    if any(k in body for k in ("small step", "incremental", "one file at a time",
                                "one change", "atomically")):
        return "incremental-editing"
    if any(k in body for k in ("assume", "without checking", "don't guess",
                                "never assert", "calibrate")):
        return "claim-calibration"
    if any(k in body for k in ("tool", "use bash", "use python", "choose the right")):
        return "tool-selection"
    if any(k in body for k in ("multi-step", "sequence", "workflow", "pipeline",
                                "then run", "then test")):
        return "multi-step-execution"

    # Domain fallback
    if domain in ("workflow",):
        return "planning"
    if domain in ("architecture",):
        return "inspection"

    return "multi-step-execution"


def build_promotion_reason(pattern: dict) -> str:
    """Compose a human-readable promotion reason from scoring data."""
    freq = pattern.get("frequency_score", 0)
    impact = pattern.get("impact_score", 0)
    sessions = pattern.get("source_sessions", 0)
    confirmations = pattern.get("confirmation_count", 0)
    source_type = pattern.get("source_type", "unknown")

    parts = [
        f"auto-scored: freq={freq:.2f}, impact={impact:.2f}",
        f"sessions={sessions}",
        f"confirmations={confirmations}",
        f"source={source_type}",
    ]
    if pattern.get("human_approved"):
        parts.append("human_approved=1")
    return "; ".join(parts)


def build_evidence_summary(pattern: dict) -> str:
    """Produce a brief evidence summary from pattern evidence JSON."""
    try:
        evidence = json.loads(pattern.get("evidence") or "[]")
    except (json.JSONDecodeError, TypeError):
        evidence = []
    if not evidence:
        return "no structured evidence"
    parts = []
    for e in evidence[:3]:
        if isinstance(e, dict):
            label = e.get("handoff") or e.get("session_id") or str(e)
            parts.append(label[:60])
    suffix = f" (+{len(evidence)-3} more)" if len(evidence) > 3 else ""
    return ", ".join(parts) + suffix if parts else "structured evidence present"


def create_artifact(pattern: dict) -> dict:
    """
    Build a portable rule artifact dict from a patterns row dict.
    Does NOT write to disk — call write_artifact() for that.
    """
    cap_class = infer_capability_class(pattern)
    mutation_scope = CAPABILITY_TO_MUTATION.get(cap_class, "prompt_overlay")

    return {
        "schema_version": "1.0",
        "pattern_id": pattern["id"],
        "created_at": _now(),
        "updated_at": _now(),
        "rule_text": (pattern.get("body") or pattern.get("title") or "").strip(),
        "source": {
            "class": pattern.get("class", "observation"),
            "domain": pattern.get("domain", "unclassified"),
            "source_type": pattern.get("source_type", "unknown"),
            "first_observed_at": pattern.get("first_observed_at"),
            "promoted_at": pattern.get("promoted_at"),
            "project_id": pattern.get("project_id"),
        },
        "promotion": {
            "reason": build_promotion_reason(pattern),
            "evidence_summary": build_evidence_summary(pattern),
            "frequency_score": pattern.get("frequency_score", 0),
            "impact_score": pattern.get("impact_score", 0),
            "confirmation_count": pattern.get("confirmation_count", 0),
            "source_sessions": pattern.get("source_sessions", 0),
        },
        "capability_class": cap_class,
        "mutation_scope": mutation_scope,
        "eval_bundle_id": None,
        "lab_runs": [],
    }


def artifact_path(pattern_id: str) -> Path:
    return ARTIFACTS_DIR / f"{pattern_id}.json"


def write_artifact(artifact: dict) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    path = artifact_path(artifact["pattern_id"])
    if path.exists():
        # Preserve lab_runs history and eval_bundle_id on update
        existing = json.loads(path.read_text())
        artifact["lab_runs"] = existing.get("lab_runs", [])
        if existing.get("eval_bundle_id") and not artifact.get("eval_bundle_id"):
            artifact["eval_bundle_id"] = existing["eval_bundle_id"]
        artifact["created_at"] = existing.get("created_at", artifact["created_at"])
    artifact["updated_at"] = _now()
    path.write_text(json.dumps(artifact, indent=2))
    return path


def read_artifact(pattern_id: str) -> dict | None:
    path = artifact_path(pattern_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def append_lab_run(pattern_id: str, run_summary: dict) -> None:
    """Append a lab run summary to the artifact's lab_runs list."""
    path = artifact_path(pattern_id)
    if not path.exists():
        return
    artifact = json.loads(path.read_text())
    artifact.setdefault("lab_runs", []).append({
        "run_id": run_summary.get("id"),
        "outcome": run_summary.get("outcome"),
        "score_delta": run_summary.get("score_delta"),
        "patch_type": run_summary.get("patch_type"),
        "recorded_at": _now(),
    })
    artifact["updated_at"] = _now()
    path.write_text(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    # Smoke test: print all existing artifacts
    if not ARTIFACTS_DIR.exists():
        print("No artifacts directory yet.")
    else:
        files = list(ARTIFACTS_DIR.glob("*.json"))
        if not files:
            print("No artifacts yet.")
        for f in files:
            a = json.loads(f.read_text())
            print(f"  {a['pattern_id'][:8]}  cap={a['capability_class']}  "
                  f"mutation={a['mutation_scope']}  runs={len(a.get('lab_runs', []))}")
