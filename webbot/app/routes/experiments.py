"""
A/B Experiment API Routes — configuration persistence for AnalyBot.

Demo posture: experiment *configuration* (name/page/split/variants/events/
audit) is persisted here so the dashboard is shareable and survives reloads.
Live traffic numbers are simulated client-side (demo mode) and synced here
as checkpoints on a throttle — a real deployment would replace the client
simulation with server-side traffic splitting (sticky cookie + hash) and
event collection via the tracking pipeline (app/routes/track.py).

Production hardening note: write endpoints currently have NO auth dependency
(matching track/references routes). Wire `get_current_active_user` from
auth_security before exposing to non-demo environments.
"""

import sqlite3
import os
import json
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])

DB_PATH = os.environ.get(
    "WEBBOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "webbot.db")
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ab_experiments (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    page          TEXT DEFAULT '',
    status        TEXT DEFAULT 'draft',
    split         INTEGER DEFAULT 50,
    confidence    REAL DEFAULT 0,
    winner        TEXT DEFAULT '',
    variants_json TEXT DEFAULT '{}',
    events_json   TEXT DEFAULT '[]',
    history_json  TEXT DEFAULT '[]',
    audit_json    TEXT DEFAULT '[]',
    created_at    TEXT DEFAULT (datetime('now','localtime')),
    created_by    TEXT DEFAULT '',
    updated_at    TEXT DEFAULT (datetime('now','localtime'))
)
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── seed demo experiments (mirrors the original front-end mock) ──

def _default_history(a_rate, b_rate):
    pts = []
    a = a_rate - 0.35
    b = b_rate - 0.55
    for _ in range(14):
        a += 0.05
        b += 0.08
        pts.append({"a": round(max(0.6, a), 3), "b": round(max(0.6, b), 3)})
    return pts


_SEED = [
    {
        "id": "exp-passport-cta",
        "name": "Passport CTA Button Test",
        "page": "/en/passport/renewal",
        "status": "running",
        "split": 50,
        "confidence": 95.2,
        "winner": "",
        "variants": {
            "A": {"label": "Variant A (Control)", "desc": "Current blue button", "visitors": 12480, "conversions": 287},
            "B": {"label": "Variant B", "desc": "Green \"Apply Now\" button", "visitors": 12501, "conversions": 388},
        },
        "events": ["CTA Click"],
        "history": _default_history(2.30, 3.10),
        "audit": [
            ["2026-08-10 09:14", "Experiment created by rita.lou — traffic split 50/50"],
            ["2026-08-10 09:15", "Conversion event \"CTA Click\" defined"],
            ["2026-08-12 11:02", "Weekly report scheduled (Mondays 08:00)"],
        ],
    },
    {
        "id": "exp-homepage-banner",
        "name": "Homepage Banner Test",
        "page": "/en",
        "status": "completed",
        "split": 50,
        "confidence": 99.1,
        "winner": "B",
        "variants": {
            "A": {"label": "Variant A (Control)", "desc": "Current banner", "visitors": 42110, "conversions": 1263},
            "B": {"label": "Variant B", "desc": "New banner — \"Find services faster\"", "visitors": 42089, "conversions": 1420},
        },
        "events": ["Banner Click"],
        "history": _default_history(2.95, 3.40),
        "audit": [
            ["2026-07-28 10:02", "Experiment created by hongbin.yu"],
            ["2026-08-02 08:00", "Variant B declared winner (+12.4% conversion, 99% confidence)"],
            ["2026-08-02 08:05", "Variant B promoted to production"],
        ],
    },
    {
        "id": "exp-services-search",
        "name": "Services Search Layout Test",
        "page": "/en/services",
        "status": "draft",
        "split": 50,
        "confidence": 0,
        "winner": "",
        "variants": {
            "A": {"label": "Variant A (Control)", "desc": "Current layout", "visitors": 0, "conversions": 0},
            "B": {"label": "Variant B", "desc": "Card-based layout", "visitors": 0, "conversions": 0},
        },
        "events": ["Search Result Click"],
        "history": _default_history(2.0, 2.0),
        "audit": [
            ["2026-08-15 16:40", "Draft created by rita.lou — pending review"],
        ],
    },
]


def _ensure_schema(conn):
    conn.execute(_SCHEMA)
    conn.commit()


def _seed_if_empty(conn):
    row = conn.execute("SELECT COUNT(*) AS c FROM ab_experiments").fetchone()
    if row["c"] == 0:
        for exp in _SEED:
            conn.execute(
                """INSERT INTO ab_experiments
                   (id, name, page, status, split, confidence, winner,
                    variants_json, events_json, history_json, audit_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    exp["id"], exp["name"], exp["page"], exp["status"],
                    exp["split"], exp["confidence"], exp["winner"],
                    json.dumps(exp["variants"]), json.dumps(exp["events"]),
                    json.dumps(exp["history"]), json.dumps(exp["audit"]),
                ),
            )
        conn.commit()


def _row_to_exp(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "page": row["page"],
        "status": row["status"],
        "split": row["split"],
        "confidence": row["confidence"],
        "winner": row["winner"],
        "variants": json.loads(row["variants_json"] or "{}"),
        "events": json.loads(row["events_json"] or "[]"),
        "history": json.loads(row["history_json"] or "[]"),
        "audit": json.loads(row["audit_json"] or "[]"),
        "created_at": row["created_at"],
        "created_by": row["created_by"],
        "updated_at": row["updated_at"],
    }


def _now():
    return time.strftime("%Y-%m-%d %H:%M")


# ── models ──

class ExperimentCreate(BaseModel):
    id: Optional[str] = None  # optional; server generates exp-<hex-ms> when omitted
    name: str
    page: str = ""
    split: int = 50
    variant_a_desc: str = ""
    variant_b_desc: str = ""
    events: List[str] = ["CTA Click"]


class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    page: Optional[str] = None
    status: Optional[str] = None
    split: Optional[int] = None
    confidence: Optional[float] = None
    winner: Optional[str] = None
    variants: Optional[Dict[str, Any]] = None
    events: Optional[List[str]] = None
    history: Optional[List[Dict[str, Any]]] = None
    audit: Optional[List[Any]] = None


# ── endpoints ──

@router.get("")
async def list_experiments():
    """List all A/B experiments (newest first)."""
    conn = get_db()
    try:
        _ensure_schema(conn)
        _seed_if_empty(conn)
        rows = conn.execute(
            "SELECT * FROM ab_experiments ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [_row_to_exp(r) for r in rows]
    finally:
        conn.close()


@router.get("/{exp_id}")
async def get_experiment(exp_id: str):
    """Get a single experiment."""
    conn = get_db()
    try:
        _ensure_schema(conn)
        _seed_if_empty(conn)
        row = conn.execute(
            "SELECT * FROM ab_experiments WHERE id = ?", (exp_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return _row_to_exp(row)
    finally:
        conn.close()


@router.post("")
async def create_experiment(body: ExperimentCreate):
    """Create an experiment. Starts in 'running' state (matches demo UX)."""
    conn = get_db()
    try:
        _ensure_schema(conn)
        if body.id and body.id.startswith("exp-") and len(body.id) <= 64:
            exp_id = body.id  # client-supplied id (e.g. matching a tracking beacon)
        else:
            exp_id = "exp-" + format(int(time.time() * 1000), "x")
        split = max(10, min(90, body.split))
        exp = {
            "id": exp_id,
            "name": body.name.strip() or "Untitled Experiment",
            "page": body.page,
            "status": "running",
            "split": split,
            "confidence": 0,
            "winner": "",
            "variants": {
                "A": {"label": "Variant A (Control)", "desc": body.variant_a_desc.strip() or "Current version",
                      "visitors": 42, "conversions": 1},
                "B": {"label": "Variant B", "desc": body.variant_b_desc.strip() or "New version",
                      "visitors": 42, "conversions": 2},
            },
            "events": body.events or ["CTA Click"],
            "history": _default_history(2.3, 3.1),
            "audit": [[_now(), f"Experiment created — traffic split {split}/{100 - split}"]],
        }
        conn.execute(
            """INSERT INTO ab_experiments
               (id, name, page, status, split, confidence, winner,
                variants_json, events_json, history_json, audit_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                exp["id"], exp["name"], exp["page"], exp["status"],
                exp["split"], exp["confidence"], exp["winner"],
                json.dumps(exp["variants"]), json.dumps(exp["events"]),
                json.dumps(exp["history"]), json.dumps(exp["audit"]),
            ),
        )
        conn.commit()
        return exp
    finally:
        conn.close()


@router.put("/{exp_id}")
async def update_experiment(exp_id: str, body: ExperimentUpdate):
    """Full/partial update. Used by the dashboard to persist every mutation
    (start/stop, events, audit entries, simulated traffic checkpoints)."""
    conn = get_db()
    try:
        _ensure_schema(conn)
        row = conn.execute(
            "SELECT * FROM ab_experiments WHERE id = ?", (exp_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Experiment not found")

        fields = {}
        if body.name is not None:
            fields["name"] = body.name.strip() or row["name"]
        if body.page is not None:
            fields["page"] = body.page
        if body.status is not None:
            fields["status"] = body.status
        if body.split is not None:
            fields["split"] = max(10, min(90, body.split))
        if body.confidence is not None:
            fields["confidence"] = body.confidence
        if body.winner is not None:
            fields["winner"] = body.winner
        if body.variants is not None:
            fields["variants_json"] = json.dumps(body.variants)
        if body.events is not None:
            fields["events_json"] = json.dumps(body.events)
        if body.history is not None:
            fields["history_json"] = json.dumps(body.history)
        if body.audit is not None:
            fields["audit_json"] = json.dumps(body.audit)

        if fields:
            fields["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            cols = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(
                f"UPDATE ab_experiments SET {cols} WHERE id = ?",
                (*fields.values(), exp_id),
            )
            conn.commit()

        updated = conn.execute(
            "SELECT * FROM ab_experiments WHERE id = ?", (exp_id,)
        ).fetchone()
        return _row_to_exp(updated)
    finally:
        conn.close()


@router.delete("/{exp_id}")
async def delete_experiment(exp_id: str):
    """Delete an experiment."""
    conn = get_db()
    try:
        _ensure_schema(conn)
        cur = conn.execute("DELETE FROM ab_experiments WHERE id = ?", (exp_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return {"deleted": exp_id}
    finally:
        conn.close()
