"""
Admin endpoints — bảo vệ bằng API key (env var ADMIN_KEY).
Mục đích chính: xuất Excel tổng hợp dữ liệu phiên học cho nghiên cứu/đồ án.
"""
from __future__ import annotations

import io
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.config import settings
from app.storage import db

router = APIRouter(tags=["admin"])


def _check_key(key: str) -> None:
    if not settings.ADMIN_KEY:
        raise HTTPException(503, "ADMIN_KEY chưa được cấu hình trên server")
    if key != settings.ADMIN_KEY:
        raise HTTPException(403, "Invalid admin key")


@router.get("/stats")
async def stats(key: str = Query(...)):
    """Số liệu nhanh: bao nhiêu phiên, bao nhiêu user, dung lượng data."""
    _check_key(key)
    rows = await db.query_sessions()
    users = {r["anonymous_id"] for r in rows}
    return {
        "total_sessions": len(rows),
        "total_users": len(users),
        "first_session": rows[-1]["started_at"] if rows else None,
        "latest_session": rows[0]["started_at"] if rows else None,
    }


@router.get("/export")
async def export_excel(
    key: str = Query(...),
    from_ts: Optional[float] = Query(None, alias="from"),
    to_ts: Optional[float] = Query(None, alias="to"),
    anonymous_id: Optional[str] = Query(None),
):
    """
    Xuất file .xlsx tổng hợp các phiên trong khoảng thời gian.
    Query params:
      - key (bắt buộc): ADMIN_KEY
      - from, to: Unix timestamp (giây) — optional
      - anonymous_id: lọc theo 1 user — optional
    """
    _check_key(key)

    rows = await db.query_sessions(
        from_ts=from_ts, to_ts=to_ts, anonymous_id=anonymous_id
    )
    if not rows:
        raise HTTPException(404, "Không có phiên nào trong khoảng đã chọn")

    # ── Sheet 1: Tổng quan (1 row/phiên) ─────────────────────────
    summary_df = pd.DataFrame([
        {
            "id": r["id"],
            "anonymous_id": r["anonymous_id"],
            "email": r["email"],
            "display_name": r["display_name"],
            "started_at": _ts_to_str(r["started_at"]),
            "ended_at": _ts_to_str(r["ended_at"]),
            "duration_min": round((r["duration_s"] or 0) / 60, 1),
            "focused_pct": r["focused_pct"],
            "distracted_pct": r["distracted_pct"],
            "on_phone_pct": r["on_phone_pct"],
            "sleepy_pct": r["sleepy_pct"],
            "distraction_episodes": r["distraction_episodes"],
            "main_cause": r["main_cause"],
        }
        for r in rows
    ])

    # ── Sheet 2: Score timeline (flattened) ──────────────────────
    scores_rows = []
    for r in rows:
        sid = r["id"]
        anon = r["anonymous_id"]
        scores = (r["payload"] or {}).get("attention_scores", [])
        for s in scores:
            scores_rows.append({
                "session_id": sid,
                "anonymous_id": anon,
                "ts": _ts_to_str(s.get("timestamp")),
                "score": s.get("score"),
                "state": s.get("state"),
                "active_composites": ", ".join(s.get("active_composites") or []),
            })
    scores_df = pd.DataFrame(scores_rows) if scores_rows else pd.DataFrame(
        columns=["session_id", "anonymous_id", "ts", "score", "state", "active_composites"]
    )

    # ── Sheet 3: Events ──────────────────────────────────────────
    events_rows = []
    for r in rows:
        sid = r["id"]; anon = r["anonymous_id"]
        for ev in (r["payload"] or {}).get("events", []):
            events_rows.append({
                "session_id": sid,
                "anonymous_id": anon,
                "event_type": ev.get("event_type"),
                "category": ev.get("category"),
                "event_group": ev.get("event_group"),
                "ts_start": _ts_to_str(ev.get("timestamp_start")),
                "ts_end": _ts_to_str(ev.get("timestamp_end")),
                "duration_ms": ev.get("duration_ms"),
                "confidence": ev.get("confidence"),
            })
    events_df = pd.DataFrame(events_rows) if events_rows else pd.DataFrame(
        columns=["session_id", "anonymous_id", "event_type", "category",
                 "event_group", "ts_start", "ts_end", "duration_ms", "confidence"]
    )

    # ── Sheet 4: Alerts ──────────────────────────────────────────
    alerts_rows = []
    for r in rows:
        sid = r["id"]; anon = r["anonymous_id"]
        for a in (r["payload"] or {}).get("alerts", []):
            alerts_rows.append({
                "session_id": sid,
                "anonymous_id": anon,
                "ts": _ts_to_str(a.get("timestamp")),
                "alert_type": a.get("alert_type"),
                "reason": a.get("reason"),
                "message": a.get("message"),
            })
    alerts_df = pd.DataFrame(alerts_rows) if alerts_rows else pd.DataFrame(
        columns=["session_id", "anonymous_id", "ts", "alert_type", "reason", "message"]
    )

    # ── Ghi file Excel vào buffer ────────────────────────────────
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        summary_df.to_excel(writer, sheet_name="Tổng quan", index=False)
        scores_df.to_excel(writer, sheet_name="Score Timeline", index=False)
        events_df.to_excel(writer, sheet_name="Events", index=False)
        alerts_df.to_excel(writer, sheet_name="Alerts", index=False)
    buf.seek(0)

    filename = "learning_sessions_export.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _ts_to_str(ts) -> Optional[str]:
    if ts is None:
        return None
    try:
        return pd.to_datetime(float(ts), unit="s").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None
