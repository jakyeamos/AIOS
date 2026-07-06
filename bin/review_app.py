#!/usr/bin/env python3
"""
AIOS Review GUI
Run: python3 ~/AIOS/bin/review_app.py
Opens: http://localhost:5001
"""

import os
import sqlite3
import uuid
import webbrowser
from datetime import UTC, datetime, timedelta

from flask import Flask, jsonify, render_template_string, request

DB = os.path.expanduser("~/AIOS/data/aios.db")
CONTRADICTION_LOG = os.path.expanduser("~/AIOS/logs/contradictions.log")
PORT = 5001

CLASS_THRESHOLDS = {
    "bug_fix": 2,
    "failure": 2,
    "error": 2,
    "architecture": 3,
    "workflow": 3,
    "assumption": 3,
    "prompt": 4,
}
DEFAULT_THRESHOLD = 3

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def record_metric(conn, metric_name: str, notes: str = "") -> None:
    conn.execute(
        """INSERT INTO workflow_metrics (id, metric_name, metric_value, recorded_at, notes)
           VALUES (?, ?, 1, ?, ?)""",
        (str(uuid.uuid4()), metric_name, utcnow(), notes or None),
    )


# ---------------------------------------------------------------------------
# Counts
# ---------------------------------------------------------------------------


@app.get("/api/counts")
def api_counts():
    conn = get_db()
    obs = conn.execute(
        "SELECT COUNT(*) FROM patterns WHERE state IN ('notice','hypothesis') AND status!='discarded' AND class!='personal'"
    ).fetchone()[0]
    bugs = conn.execute("SELECT COUNT(*) FROM bug_log").fetchone()[0]
    rules = conn.execute(
        "SELECT COUNT(*) FROM patterns WHERE state='rule' AND class!='personal'"
    ).fetchone()[0]
    personal = conn.execute(
        "SELECT COUNT(*) FROM patterns WHERE class='personal' AND status!='discarded' AND human_approved=0"
    ).fetchone()[0]
    high_signal = conn.execute(
        """SELECT COUNT(*) FROM patterns
           WHERE source_type IN ('handoff-learned','tool-error','agent-synthesis')
             AND confidence >= 0.5 AND body IS NOT NULL AND body != ''
             AND human_approved=0 AND status!='discarded'"""
    ).fetchone()[0]
    conn.close()
    return jsonify(
        {
            "observations": obs,
            "bugs": bugs,
            "rules": rules,
            "personal": personal,
            "high_signal": high_signal,
        }
    )


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------


@app.get("/api/observations")
def api_observations():
    domain = request.args.get("domain", "")
    conn = get_db()
    state = request.args.get("state", "")
    q = "SELECT * FROM patterns WHERE state IN ('notice','hypothesis') AND status!='discarded'"
    params: list = []
    if state in ("notice", "hypothesis"):
        q = "SELECT * FROM patterns WHERE state=? AND status!='discarded'"
        params.append(state)
    if domain:
        q += " AND domain=?"
        params.append(domain)
    q += " ORDER BY (frequency_score + impact_score) DESC LIMIT 100"
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    return jsonify(rows)


@app.post("/api/observations/<pid>/approve")
def api_obs_approve(pid):
    """Directly approve an observation as a rule — no intermediate state."""
    conn = get_db()
    row = conn.execute("SELECT class, domain FROM patterns WHERE id=?", (pid,)).fetchone()
    conn.execute(
        "UPDATE patterns SET state='rule', status='active', human_approved=1, promoted_at=? WHERE id=?",
        (utcnow(), pid),
    )
    record_metric(
        conn,
        "review_approve",
        f"class={row['class'] if row else ''} domain={row['domain'] if row else ''}",
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.post("/api/observations/<pid>/discard")
def api_obs_discard(pid):
    conn = get_db()
    row = conn.execute("SELECT class, domain FROM patterns WHERE id=?", (pid,)).fetchone()
    conn.execute("UPDATE patterns SET status='discarded' WHERE id=?", (pid,))
    record_metric(
        conn,
        "review_discard",
        f"class={row['class'] if row else ''} domain={row['domain'] if row else ''}",
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------


@app.get("/api/approve")
def api_approve_list():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM patterns WHERE state='knowledge' AND human_approved=0 ORDER BY confidence DESC"
    ).fetchall()
    cutoff = (datetime.now(UTC) - timedelta(days=14)).isoformat()
    result = []
    for r in rows:
        p = dict(r)
        threshold = CLASS_THRESHOLDS.get(p.get("class", ""), DEFAULT_THRESHOLD)
        distinct_sessions = conn.execute(
            """SELECT COUNT(DISTINCT session_id) FROM pattern_events
               WHERE pattern_id=? AND event_type='confirmation'""",
            (p["id"],),
        ).fetchone()[0]
        gates = {
            "confirmations": (p.get("confirmation_count") or 0) >= threshold,
            "confirmations_detail": f"{p.get('confirmation_count') or 0}/{threshold}",
            "age": (p.get("first_observed_at") or "") <= cutoff,
            "age_detail": (p.get("first_observed_at") or "")[:10],
            "sessions": distinct_sessions >= 2,
            "sessions_detail": f"{distinct_sessions} distinct",
        }
        p["gates"] = gates
        p["gates_pass"] = all([gates["confirmations"], gates["age"], gates["sessions"]])
        result.append(p)
    conn.close()
    return jsonify(result)


@app.post("/api/approve/<pid>")
def api_approve(pid):
    conn = get_db()
    row = conn.execute("SELECT * FROM patterns WHERE id=?", (pid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "not found"}), 404
    p = dict(row)
    cutoff = (datetime.now(UTC) - timedelta(days=14)).isoformat()
    threshold = CLASS_THRESHOLDS.get(p.get("class", ""), DEFAULT_THRESHOLD)
    distinct_sessions = conn.execute(
        """SELECT COUNT(DISTINCT session_id) FROM pattern_events
           WHERE pattern_id=? AND event_type='confirmation'""",
        (pid,),
    ).fetchone()[0]
    gate_fails = []
    if (p.get("confirmation_count") or 0) < threshold:
        gate_fails.append(
            f"needs {threshold} confirmations (has {p.get('confirmation_count') or 0})"
        )
    if (p.get("first_observed_at") or "") > cutoff:
        gate_fails.append("pattern is less than 14 days old")
    if distinct_sessions < 2:
        gate_fails.append(f"needs 2 distinct sessions (has {distinct_sessions})")
    if gate_fails:
        conn.close()
        return jsonify({"ok": False, "gate_fails": gate_fails}), 422
    conn.execute(
        "UPDATE patterns SET human_approved=1, state='rule', promoted_at=? WHERE id=?",
        (utcnow(), pid),
    )
    record_metric(
        conn, "review_approve", f"class={p.get('class', '')} domain={p.get('domain', '')}"
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Bug log
# ---------------------------------------------------------------------------


@app.get("/api/bugs")
def api_bugs():
    conn = get_db()
    rows = [
        dict(r)
        for r in conn.execute("SELECT * FROM bug_log ORDER BY created_at DESC LIMIT 200").fetchall()
    ]
    # Attach linked pattern id for each bug (stored in pattern evidence JSON)
    for row in rows:
        linked = conn.execute(
            """SELECT id, title, state FROM patterns
               WHERE evidence LIKE ? AND source_type='tool-error' LIMIT 1""",
            (f'%"bug_id": "{row["id"]}"%',),
        ).fetchone()
        row["linked_pattern"] = dict(linked) if linked else None
    conn.close()
    return jsonify(rows)


# ---------------------------------------------------------------------------
# Confirm / Contradict
# ---------------------------------------------------------------------------


@app.get("/api/patterns/search")
def api_pattern_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    conn = get_db()
    rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM patterns WHERE title LIKE ? AND status!='discarded' ORDER BY confidence DESC LIMIT 20",
            (f"%{q}%",),
        ).fetchall()
    ]
    conn.close()
    return jsonify(rows)


@app.post("/api/patterns/<pid>/confirm")
def api_confirm(pid):
    note = (request.json or {}).get("note", "")
    conn = get_db()
    row = conn.execute("SELECT * FROM patterns WHERE id=?", (pid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "not found"}), 404
    p = dict(row)
    new_conf = min((p.get("confidence") or 0.5) + 0.05, 0.95)
    new_count = (p.get("confirmation_count") or 0) + 1
    conn.execute(
        "UPDATE patterns SET confirmation_count=?, confidence=?, last_confirmed_at=? WHERE id=?",
        (new_count, new_conf, utcnow(), pid),
    )
    conn.execute(
        """INSERT INTO pattern_events (id, pattern_id, event_type, source_type, notes, event_time)
           VALUES (?, ?, 'confirmation', 'manual', ?, ?)""",
        (str(uuid.uuid4()), pid, note or None, utcnow()),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "confidence": new_conf, "confirmation_count": new_count})


@app.post("/api/patterns/<pid>/contradict")
def api_contradict(pid):
    note = (request.json or {}).get("note", "")
    if not note:
        return jsonify({"ok": False, "error": "note is required for contradictions"}), 422
    conn = get_db()
    row = conn.execute("SELECT * FROM patterns WHERE id=?", (pid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "not found"}), 404
    p = dict(row)
    old_state = p.get("state", "")
    new_conf = max((p.get("confidence") or 0.5) - 0.15, 0.10)
    new_count = (p.get("contradiction_count") or 0) + 1
    new_state = "hypothesis" if old_state == "rule" else old_state
    human_approved = 0 if new_state == "hypothesis" else p.get("human_approved", 0)
    conn.execute(
        """UPDATE patterns SET contradiction_count=?, confidence=?, last_contradicted_at=?,
           state=?, human_approved=? WHERE id=?""",
        (new_count, new_conf, utcnow(), new_state, human_approved, pid),
    )
    conn.execute(
        """INSERT INTO pattern_events (id, pattern_id, event_type, source_type, notes, event_time)
           VALUES (?, ?, 'contradiction', 'manual', ?, ?)""",
        (str(uuid.uuid4()), pid, note, utcnow()),
    )
    conn.commit()
    try:
        os.makedirs(os.path.dirname(CONTRADICTION_LOG), exist_ok=True)
        with open(CONTRADICTION_LOG, "a") as f:
            f.write(f"{utcnow()}  [{old_state}→{new_state}]  {p['title'][:80]}\n  note: {note}\n\n")
    except Exception:
        pass
    conn.close()
    return jsonify({"ok": True, "confidence": new_conf, "state": new_state})


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


@app.get("/api/personal")
def api_personal():
    sub_class = request.args.get("sub_class", "")
    conn = get_db()
    q = "SELECT * FROM patterns WHERE class='personal' AND status!='discarded'"
    params: list = []
    if sub_class:
        q += " AND domain=?"
        params.append(sub_class)
    q += " ORDER BY human_approved ASC, confidence DESC LIMIT 200"
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    return jsonify(rows)


@app.post("/api/personal/<pid>/approve")
def api_personal_approve(pid):
    """Mark a personal pattern as human-approved (ready for vault promotion)."""
    conn = get_db()
    row = conn.execute("SELECT domain FROM patterns WHERE id=?", (pid,)).fetchone()
    conn.execute(
        "UPDATE patterns SET human_approved=1, state='rule' WHERE id=?",
        (pid,),
    )
    record_metric(conn, "review_personal_approve", f"sub_class={row['domain'] if row else ''}")
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.post("/api/personal/<pid>/discard")
def api_personal_discard(pid):
    conn = get_db()
    conn.execute("UPDATE patterns SET status='discarded' WHERE id=?", (pid,))
    record_metric(conn, "review_personal_discard", "")
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.post("/api/personal/<pid>/promote-vault")
def api_personal_promote_vault(pid):
    """Write an approved personal pattern to the Obsidian mental map."""
    import subprocess
    import sys

    conn = get_db()
    row = conn.execute("SELECT * FROM patterns WHERE id=?", (pid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "not found"}), 404
    p = dict(row)
    if not p.get("human_approved"):
        conn.close()
        return jsonify({"ok": False, "error": "approve first"}), 422
    conn.close()
    # Run promote script for just this pattern — it checks vault_path IS NULL
    try:
        result = subprocess.run(
            [sys.executable, os.path.expanduser("~/AIOS/bin/promote-personal-patterns.py")],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return jsonify({"ok": True, "output": result.stdout.strip()})
        return jsonify({"ok": False, "error": result.stderr.strip()[:200]}), 500
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.get("/api/high-signal")
def api_high_signal():
    """Filtered queue: high-signal source types, confidence >= 0.5, body present, not yet approved."""
    conn = get_db()
    rows = [
        dict(r)
        for r in conn.execute(
            """SELECT * FROM patterns
           WHERE source_type IN ('handoff-learned', 'tool-error', 'agent-synthesis')
             AND confidence >= 0.5
             AND body IS NOT NULL AND body != ''
             AND human_approved = 0
             AND status != 'discarded'
           ORDER BY confidence DESC, created_at ASC
           LIMIT 100""",
        ).fetchall()
    ]
    conn.close()
    return jsonify(rows)


@app.post("/api/high-signal/<pid>/approve")
def api_high_signal_approve(pid):
    conn = get_db()
    row = conn.execute("SELECT class, domain FROM patterns WHERE id=?", (pid,)).fetchone()
    conn.execute(
        "UPDATE patterns SET state='rule', status='active', human_approved=1, promoted_at=? WHERE id=?",
        (utcnow(), pid),
    )
    record_metric(
        conn,
        "review_high_signal_approve",
        f"class={row['class'] if row else ''} domain={row['domain'] if row else ''}",
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.post("/api/high-signal/<pid>/discard")
def api_high_signal_discard(pid):
    conn = get_db()
    conn.execute("UPDATE patterns SET status='discarded' WHERE id=?", (pid,))
    record_metric(conn, "review_high_signal_discard", "")
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.get("/api/rules")
def api_rules():
    conn = get_db()
    rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM patterns WHERE state='rule' ORDER BY confidence DESC"
        ).fetchall()
    ]
    conn.close()
    return jsonify(rows)


# ---------------------------------------------------------------------------
# Frontend — all user data rendered via textContent (no innerHTML interpolation)
# ---------------------------------------------------------------------------

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AIOS Review</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'SF Mono', 'Fira Code', monospace; background: #0f0f1a; color: #e0e0e0;
         display: flex; height: 100vh; overflow: hidden; font-size: 12px; }

  #sidebar { width: 174px; background: #16213e; display: flex; flex-direction: column;
             padding: 14px 8px; gap: 2px; flex-shrink: 0; }
  .logo { color: #7c83fd; font-size: 13px; font-weight: bold; padding: 6px 8px; margin-bottom: 10px; }
  .nav-item { display: flex; align-items: center; justify-content: space-between;
              padding: 7px 10px; border-radius: 5px; cursor: pointer; color: #888; }
  .nav-item:hover { background: #1e2a4a; color: #ccc; }
  .nav-item.active { background: #2a2a4a; color: #fff; }
  .badge { font-size: 9px; padding: 1px 6px; border-radius: 8px; background: #2a2a4a; }
  .badge.blue { color: #7c83fd; } .badge.amber { color: #f59e0b; }
  .badge.red { color: #f87171; } .badge.green { color: #4ade80; }
  .sidebar-footer { margin-top: auto; color: #333; font-size: 9px; padding: 8px 10px;
                    border-top: 1px solid #1e2a4a; }

  #main { flex: 1; overflow-y: auto; padding: 20px 24px; }
  .section { display: none; }
  .section.active { display: block; }
  .section-title { font-size: 14px; font-weight: bold; margin-bottom: 4px; }
  .section-sub { color: #555; font-size: 10px; margin-bottom: 14px; }

  .filter-row { display: flex; gap: 8px; margin-bottom: 12px; }
  select, input[type=text] { background: #16213e; border: 1px solid #2a2a4a; color: #ccc;
                              padding: 5px 10px; border-radius: 4px; font-size: 11px; font-family: inherit; }
  select:focus, input[type=text]:focus { outline: 1px solid #7c83fd; }

  .pattern-row { background: #16213e; border-radius: 5px; padding: 9px 12px;
                 display: flex; align-items: center; gap: 12px; border-left: 3px solid #2a2a4a;
                 margin-bottom: 5px; transition: opacity 0.2s; }
  .pattern-info { flex: 1; min-width: 0; }
  .pattern-title { color: #d0d0d0; font-size: 11px; line-height: 1.4; }
  .pattern-meta { display: flex; gap: 6px; margin-top: 4px; flex-wrap: wrap; align-items: center; }
  .tag { font-size: 9px; padding: 1px 5px; border-radius: 2px; background: #2a2a3a; color: #888; }

  .actions { display: flex; gap: 4px; flex-shrink: 0; }
  button { font-family: inherit; font-size: 10px; padding: 4px 9px; border: none;
           border-radius: 3px; cursor: pointer; }
  button:hover { opacity: 0.85; } button:disabled { opacity: 0.4; cursor: default; }
  .btn-promote { background: #1a3a2a; color: #4ade80; }
  .btn-discard { background: #3a1a1a; color: #f87171; }
  .btn-approve { background: #f59e0b; color: #111; font-weight: bold; }
  .btn-confirm { background: #1a3a2a; color: #4ade80; }
  .btn-contradict { background: #3a1a1a; color: #f87171; }
  .btn-resolve { background: #2a2a3a; color: #888; }

  .bug-row { background: #16213e; border-radius: 5px; padding: 9px 12px; margin-bottom: 5px;
             border-left: 3px solid #f87171; display: flex; align-items: flex-start;
             justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .bug-promoted { border-left-color: #4ade80; opacity: 0.6; }
  .bug-info { flex: 1; min-width: 0; }
  .bug-symptom { font-size: 11px; color: #d0d0d0; }
  .bug-meta { font-size: 9px; color: #555; margin-top: 3px; }
  .bug-root-cause { font-size: 10px; color: #4ade80; margin-top: 4px; font-style: italic; }
  .bug-actions { flex-shrink: 0; }
  .bug-badge-promoted { font-size: 8px; padding: 2px 7px; border-radius: 3px;
                        background: #1a3a2a; color: #4ade80; flex-shrink: 0; align-self: flex-start; }

  .rule-row { background: #16213e; border-radius: 5px; padding: 9px 12px; margin-bottom: 5px;
              border-left: 3px solid #4ade80; display: flex; align-items: center;
              justify-content: space-between; gap: 12px; }
  .rule-info { flex: 1; }
  .rule-title { font-size: 11px; color: #d0d0d0; }
  .rule-badge { font-size: 8px; padding: 2px 6px; border-radius: 3px;
                background: #1a3a2a; color: #4ade80; border: 1px solid #1a3a2a; flex-shrink: 0; }



  .empty { text-align: center; color: #444; padding: 48px 0; font-size: 11px; }

  #toast { position: fixed; bottom: 24px; right: 24px; background: #2a2a4a; color: #ccc;
           padding: 8px 14px; border-radius: 5px; font-size: 11px; opacity: 0;
           transition: opacity 0.3s; pointer-events: none; border-left: 3px solid #4ade80; }
  #toast.show { opacity: 1; }
  #toast.error { border-left-color: #f87171; }


  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #0f0f1a; }
  ::-webkit-scrollbar-thumb { background: #2a2a4a; border-radius: 3px; }
</style>
</head>
<body>

<nav id="sidebar">
  <div class="logo">AIOS Review</div>
  <div class="nav-item active" data-section="observations" onclick="nav(this)">
    Observations <span class="badge blue" id="badge-observations">…</span>
  </div>
  <div class="nav-item" data-section="bugs" onclick="nav(this)">
    Bug Log <span class="badge red" id="badge-bugs">…</span>
  </div>
  <div class="nav-item" data-section="high-signal" onclick="nav(this)">
    High Signal <span class="badge amber" id="badge-high-signal">…</span>
  </div>
  <div class="nav-item" data-section="personal" onclick="nav(this)">
    Personal <span class="badge amber" id="badge-personal">…</span>
  </div>
  <div class="nav-item" data-section="rules" onclick="nav(this)">
    Rules <span class="badge green" id="badge-rules">…</span>
  </div>
  <div class="sidebar-footer">aios.db · live</div>
</nav>

<main id="main">

  <div class="section active" id="section-observations">
    <div class="section-title">Pipeline</div>
    <div class="section-sub">notice → hypothesis → rule · sorted by frequency + impact · approve to make a rule · discard noise</div>
    <div class="filter-row">
      <select id="obs-state-filter" onchange="loadObservations()">
        <option value="">All states</option>
        <option value="hypothesis">hypothesis</option>
        <option value="notice">notice</option>
      </select>
      <select id="obs-domain-filter" onchange="loadObservations()">
        <option value="">All domains</option>
        <option value="tooling">tooling</option>
        <option value="architecture">architecture</option>
        <option value="workflow">workflow</option>
        <option value="debugging">debugging</option>
        <option value="prompting">prompting</option>
        <option value="unclassified">unclassified</option>
      </select>
    </div>
    <div id="obs-list"></div>
  </div>

  <div class="section" id="section-bugs">
    <div class="section-title">Bug Log</div>
    <div class="section-sub">errors auto-captured and seeded into Observations · review them there</div>
    <div id="bugs-list"></div>
  </div>

  <div class="section" id="section-high-signal">
    <div class="section-title">High Signal</div>
    <div class="section-sub">source: handoff-learned · tool-error · agent-synthesis · confidence ≥ 0.50 · body present · pending review</div>
    <div id="high-signal-list"></div>
  </div>

  <div class="section" id="section-personal">
    <div class="section-title">Personal Patterns</div>
    <div class="section-sub">mined from your sessions · approve → queued for Obsidian · discard noise</div>
    <div class="filter-row">
      <select id="personal-filter" onchange="loadPersonal()">
        <option value="">All sub-classes</option>
        <option value="preference">preference</option>
        <option value="learning">learning</option>
        <option value="blindspot">blindspot</option>
        <option value="habit">habit</option>
      </select>
      <select id="personal-approved-filter" onchange="loadPersonal()">
        <option value="pending">Pending review</option>
        <option value="approved">Approved</option>
        <option value="all">All</option>
      </select>
    </div>
    <div id="personal-list"></div>
  </div>

  <div class="section" id="section-rules">
    <div class="section-title">Active Rules</div>
    <div class="section-sub">human-approved · read-only</div>
    <div id="rules-list"></div>
  </div>

</main>


<div id="toast"></div>

<script>
// ---------------------------------------------------------------------------
// DOM helpers — user data always goes through textContent, never innerHTML
// ---------------------------------------------------------------------------
function el(tag, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  return node;
}
function txt(tag, content, className) {
  const node = el(tag, className);
  node.textContent = content;
  return node;
}
function append(parent, ...children) {
  children.forEach(c => c && parent.appendChild(c));
  return parent;
}
function empty(msg) {
  return txt('div', msg || 'Nothing here.', 'empty');
}

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------
const sectionLoaders = {
  observations: loadObservations,
  bugs: loadBugs,
  'high-signal': loadHighSignal,
  personal: loadPersonal,
  rules: loadRules,
};

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------
let toastTimer;
function toast(msg, isError) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = isError ? 'show error' : 'show';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2800);
}

// ---------------------------------------------------------------------------
// Counts
// ---------------------------------------------------------------------------
async function refreshCounts() {
  const d = await fetch('/api/counts').then(r => r.json());
  document.getElementById('badge-observations').textContent = d.observations;
  document.getElementById('badge-bugs').textContent = d.bugs;
  document.getElementById('badge-high-signal').textContent = d.high_signal ?? 0;
  document.getElementById('badge-rules').textContent = d.rules;
  document.getElementById('badge-personal').textContent = d.personal ?? 0;
}

// ---------------------------------------------------------------------------
// Colour helpers
// ---------------------------------------------------------------------------
const CLASS_COLORS = {
  error: '#f87171', architecture: '#7c83fd', workflow: '#4ade80',
  bug_fix: '#f59e0b', failure: '#f87171', assumption: '#a78bfa', prompt: '#38bdf8',
};
function classColor(c) { return CLASS_COLORS[c] || '#888'; }
function confClass(v) {
  if (v < 0.4) return 'conf-low';
  if (v < 0.7) return 'conf-med';
  return 'conf-high';
}

// ---------------------------------------------------------------------------
// Shared pattern meta row
// ---------------------------------------------------------------------------
function metaRow(p) {
  const meta = el('div', 'pattern-meta');
  const cls = txt('span', p.class || '—', 'tag');
  cls.style.color = classColor(p.class);
  const dom = txt('span', p.domain || '—', 'tag');
  const conf = txt('span', 'conf ' + (p.confidence || 0).toFixed(2), 'tag ' + confClass(p.confidence || 0));
  const src = txt('span', p.source_type || '', 'tag');
  return append(meta, cls, dom, conf, src);
}

// ---------------------------------------------------------------------------
// Observations
// ---------------------------------------------------------------------------
async function loadObservations() {
  const domain = document.getElementById('obs-domain-filter').value;
  const state  = document.getElementById('obs-state-filter').value;
  const params = new URLSearchParams();
  if (domain) params.set('domain', domain);
  if (state)  params.set('state', state);
  const url = '/api/observations' + (params.toString() ? '?' + params.toString() : '');
  const rows = await fetch(url).then(r => r.json());
  const list = document.getElementById('obs-list');
  list.replaceChildren();
  if (!rows.length) { list.appendChild(empty('Nothing at this filter level.')); return; }
  rows.forEach(p => list.appendChild(makeObsRow(p)));
}

function makeObsRow(p) {
  const row = el('div', 'pattern-row');
  row.id = 'obs-' + p.id;
  row.style.borderLeftColor = classColor(p.class);

  const info = el('div', 'pattern-info');
  const stateBadge = txt('span', p.state, 'tag');
  stateBadge.style.color = p.state === 'hypothesis' ? '#f59e0b' : '#888';
  const freqTag = txt('span', 'freq ' + (p.frequency_score || 0).toFixed(2), 'tag');
  const impTag  = txt('span', 'imp '  + (p.impact_score  || 0).toFixed(2), 'tag');
  const scores = el('div', 'pattern-meta');
  append(scores, stateBadge, freqTag, impTag);
  append(info, txt('div', p.title, 'pattern-title'), metaRow(p), scores);

  const actions = el('div', 'actions');
  const btnApprove = txt('button', '✓ Rule', 'btn-approve');
  const btnDiscard = txt('button', '✕', 'btn-discard');
  btnApprove.onclick = () => obsApprove(p.id);
  btnDiscard.onclick = () => obsDiscard(p.id);
  append(actions, btnApprove, btnDiscard);

  return append(row, info, actions);
}

async function obsApprove(id) {
  await fetch('/api/observations/' + id + '/approve', { method: 'POST' });
  const r = document.getElementById('obs-' + id);
  if (r) { r.style.opacity = '0'; setTimeout(() => r.remove(), 200); }
  toast('Approved as rule ✓');
  refreshCounts();
}

async function obsDiscard(id) {
  await fetch('/api/observations/' + id + '/discard', { method: 'POST' });
  const r = document.getElementById('obs-' + id);
  if (r) { r.style.opacity = '0'; setTimeout(() => r.remove(), 200); }
  toast('Discarded');
  refreshCounts();
}


// ---------------------------------------------------------------------------
// Bug log
// ---------------------------------------------------------------------------
async function loadBugs() {
  const rows = await fetch('/api/bugs').then(r => r.json());
  const list = document.getElementById('bugs-list');
  list.replaceChildren();
  if (!rows.length) { list.appendChild(empty('No errors captured yet.')); return; }
  rows.forEach(b => list.appendChild(makeBugRow(b)));
}

function makeBugRow(b) {
  const row = el('div', 'bug-row');
  row.id = 'bug-' + b.id;

  const info = el('div', 'bug-info');
  const ts = (b.created_at || '').slice(0, 16).replace('T', ' ');
  const metaParts = [ts];
  if (b.project_id) metaParts.push(b.project_id);
  if (b.linked_pattern) metaParts.push('→ ' + b.linked_pattern.state);
  append(info,
    txt('div', b.symptom, 'bug-symptom'),
    txt('div', metaParts.join(' · '), 'bug-meta'),
  );

  const badge = txt('span', 'in observations', 'bug-badge-promoted');
  return append(row, info, badge);
}


// ---------------------------------------------------------------------------
// Rules
// ---------------------------------------------------------------------------
async function loadRules() {
  const rows = await fetch('/api/rules').then(r => r.json());
  const list = document.getElementById('rules-list');
  list.replaceChildren();
  if (!rows.length) { list.appendChild(empty('No rules yet.')); return; }
  rows.forEach(p => {
    const row = el('div', 'rule-row');
    const info = el('div', 'rule-info');
    const meta = el('div', 'pattern-meta');
    meta.style.marginTop = '4px';
    const cls = txt('span', p.class || '—', 'tag');
    cls.style.color = classColor(p.class);
    const dom = txt('span', p.domain || '—', 'tag');
    const conf = txt('span', 'conf ' + (p.confidence || 0).toFixed(2), 'tag ' + confClass(p.confidence || 0));
    const confs = txt('span', (p.confirmation_count || 0) + ' confirmations', 'tag');
    append(meta, cls, dom, conf, confs);
    append(info, txt('div', p.title, 'rule-title'), meta);
    append(row, info, txt('span', 'rule', 'rule-badge'));
    list.appendChild(row);
  });
}

// ---------------------------------------------------------------------------
// High Signal queue
// ---------------------------------------------------------------------------
async function loadHighSignal() {
  const rows = await fetch('/api/high-signal').then(r => r.json());
  const list = document.getElementById('high-signal-list');
  list.replaceChildren();
  if (!rows.length) { list.appendChild(empty('No high-signal candidates pending review.')); return; }
  rows.forEach(p => list.appendChild(makeHighSignalRow(p)));
}

function makeHighSignalRow(p) {
  const row = el('div', 'pattern-row');
  row.id = 'hs-' + p.id;
  row.style.borderLeftColor = classColor(p.class);

  const info = el('div', 'pattern-info');
  const title = txt('div', p.title, 'pattern-title');
  const bodyEl = el('div', 'pattern-title');
  bodyEl.textContent = (p.body || '').slice(0, 160);
  bodyEl.style.cssText = 'color:#888;font-size:10px;margin-top:3px;';
  const meta = metaRow(p);
  const srcTag = txt('span', p.source_type || '', 'tag');
  srcTag.style.color = '#f59e0b';
  meta.appendChild(srcTag);
  append(info, title, bodyEl, meta);

  const actions = el('div', 'actions');
  const btnApprove = txt('button', '✓ Rule', 'btn-approve');
  const btnDiscard = txt('button', '✕', 'btn-discard');
  btnApprove.onclick = () => hsApprove(p.id);
  btnDiscard.onclick = () => hsDiscard(p.id);
  append(actions, btnApprove, btnDiscard);

  return append(row, info, actions);
}

async function hsApprove(id) {
  await fetch('/api/high-signal/' + id + '/approve', { method: 'POST' });
  const r = document.getElementById('hs-' + id);
  if (r) { r.style.opacity = '0'; setTimeout(() => r.remove(), 200); }
  toast('Approved as rule ✓');
  refreshCounts();
}

async function hsDiscard(id) {
  await fetch('/api/high-signal/' + id + '/discard', { method: 'POST' });
  const r = document.getElementById('hs-' + id);
  if (r) { r.style.opacity = '0'; setTimeout(() => r.remove(), 200); }
  toast('Discarded');
  refreshCounts();
}

// ---------------------------------------------------------------------------
// Personal patterns
// ---------------------------------------------------------------------------
const SUBCLASS_COLORS = {
  preference: '#7c83fd', learning: '#38bdf8', blindspot: '#f87171', habit: '#4ade80',
};

async function loadPersonal() {
  const sub_class = document.getElementById('personal-filter').value;
  const approved  = document.getElementById('personal-approved-filter').value;
  const params    = new URLSearchParams();
  if (sub_class) params.set('sub_class', sub_class);
  const url = '/api/personal' + (params.toString() ? '?' + params.toString() : '');
  let rows = await fetch(url).then(r => r.json());

  if (approved === 'pending')  rows = rows.filter(p => !p.human_approved);
  if (approved === 'approved') rows = rows.filter(p =>  p.human_approved);

  const list = document.getElementById('personal-list');
  list.replaceChildren();
  if (!rows.length) { list.appendChild(empty('Nothing at this filter level.')); return; }
  rows.forEach(p => list.appendChild(makePersonalRow(p)));
}

function makePersonalRow(p) {
  const row = el('div', 'pattern-row');
  row.id = 'personal-' + p.id;
  const subclass = p.domain || 'unclassified';
  row.style.borderLeftColor = SUBCLASS_COLORS[subclass] || '#888';

  const info = el('div', 'pattern-info');
  const scBadge = txt('span', subclass, 'tag');
  scBadge.style.color = SUBCLASS_COLORS[subclass] || '#888';
  const confTag = txt('span', 'conf ' + (p.confidence || 0).toFixed(2), 'tag');
  const approvedTag = p.human_approved ? txt('span', '✓ approved', 'tag') : null;
  approvedTag && (approvedTag.style.color = '#4ade80');
  const vaultTag = p.vault_path ? txt('span', '→ vault', 'tag') : null;
  vaultTag && (vaultTag.style.color = '#38bdf8');
  const meta = el('div', 'pattern-meta');
  append(meta, scBadge, confTag, approvedTag, vaultTag);
  append(info, txt('div', p.title, 'pattern-title'), meta);

  const actions = el('div', 'actions');

  if (!p.human_approved) {
    const btnApprove = txt('button', '✓ Approve', 'btn-approve');
    btnApprove.onclick = () => personalApprove(p.id);
    actions.appendChild(btnApprove);
  } else if (!p.vault_path) {
    const btnVault = txt('button', '→ Vault', 'btn-confirm');
    btnVault.onclick = () => personalPromoteVault(p.id);
    actions.appendChild(btnVault);
  }

  const btnDiscard = txt('button', '✕', 'btn-discard');
  btnDiscard.onclick = () => personalDiscard(p.id);
  actions.appendChild(btnDiscard);

  return append(row, info, actions);
}

async function personalApprove(id) {
  const res = await fetch('/api/personal/' + id + '/approve', { method: 'POST' });
  const data = await res.json();
  if (data.ok) {
    toast('Approved — run promote-personal-patterns.py or click → Vault');
    loadPersonal(); refreshCounts();
  } else {
    toast(data.error || 'Error', true);
  }
}

async function personalPromoteVault(id) {
  const btn = document.querySelector('#personal-' + id + ' .btn-confirm');
  if (btn) { btn.disabled = true; btn.textContent = '…'; }
  const res = await fetch('/api/personal/' + id + '/promote-vault', { method: 'POST' });
  const data = await res.json();
  if (data.ok) {
    toast('Written to Obsidian Mental Map ✓');
    loadPersonal(); refreshCounts();
  } else {
    toast(data.error || 'Vault write failed', true);
    if (btn) { btn.disabled = false; btn.textContent = '→ Vault'; }
  }
}

async function personalDiscard(id) {
  await fetch('/api/personal/' + id + '/discard', { method: 'POST' });
  const r = document.getElementById('personal-' + id);
  if (r) { r.style.opacity = '0'; setTimeout(() => r.remove(), 200); }
  toast('Discarded');
  refreshCounts();
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
let currentSection = 'observations';

function nav(el) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  el.classList.add('active');
  currentSection = el.dataset.section;
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById('section-' + currentSection).classList.add('active');
  if (sectionLoaders[currentSection]) sectionLoaders[currentSection]();
}

// Poll: refresh badges + active section every 15s
setInterval(() => {
  refreshCounts();
  if (sectionLoaders[currentSection]) sectionLoaders[currentSection]();
}, 15000);

refreshCounts();
loadObservations();
</script>
</body>
</html>
"""


@app.get("/")
def index():
    return render_template_string(HTML)


if __name__ == "__main__":
    print(f"\\nAIOS Review → http://localhost:{PORT}\\n")
    webbrowser.open(f"http://localhost:{PORT}")
    app.run(port=PORT, debug=False, use_reloader=False)
