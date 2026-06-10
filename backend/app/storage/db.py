"""
Async Postgres persistence layer (Supabase / Render Postgres / Neon).

Graceful fallback — nếu DATABASE_URL không có hoặc DB không kết nối được,
toàn bộ pipeline vẫn chạy bình thường (chỉ là không persist gì cả).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

try:
    import asyncpg  # type: ignore
except ImportError:
    asyncpg = None  # type: ignore

logger = logging.getLogger(__name__)

_pool: Optional[Any] = None

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS session_logs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  anonymous_id    TEXT NOT NULL,
  email           TEXT,
  display_name    TEXT,
  consent_given   BOOLEAN NOT NULL DEFAULT FALSE,
  started_at      TIMESTAMPTZ NOT NULL,
  ended_at        TIMESTAMPTZ,
  duration_s      INTEGER,
  focused_pct     REAL,
  distracted_pct  REAL,
  on_phone_pct    REAL,
  sleepy_pct      REAL,
  distraction_episodes INTEGER,
  main_cause      TEXT,
  payload         JSONB NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_session_logs_anon ON session_logs(anonymous_id);
CREATE INDEX IF NOT EXISTS idx_session_logs_created ON session_logs(created_at);
"""


async def _set_jsonb_codec(conn) -> None:
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def init_pool() -> None:
    global _pool
    if asyncpg is None:
        logger.info("asyncpg chưa cài — DB persistence tắt")
        return
    url = os.getenv("DATABASE_URL")
    if not url:
        logger.info("DATABASE_URL chưa set — DB persistence tắt")
        return
    try:
        _pool = await asyncpg.create_pool(
            url, min_size=1, max_size=5, init=_set_jsonb_codec
        )
        async with _pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)
        logger.info("DB pool đã sẵn sàng + schema OK")
    except Exception as e:
        logger.error(f"init_pool lỗi — chạy không có DB: {e}")
        _pool = None


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def is_enabled() -> bool:
    return _pool is not None


async def flush_session(
    *,
    anonymous_id: str,
    email: Optional[str],
    display_name: Optional[str],
    consent_given: bool,
    started_at: float,
    ended_at: float,
    analysis: dict[str, Any],
    full_payload: dict[str, Any],
) -> None:
    """Ghi 1 phiên đã kết thúc vào DB. Bỏ qua nếu chưa đồng ý nghiên cứu."""
    if _pool is None or not consent_given:
        return
    duration_s = int(max(0, ended_at - started_at))
    try:
        async with _pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO session_logs (
                    anonymous_id, email, display_name, consent_given,
                    started_at, ended_at, duration_s,
                    focused_pct, distracted_pct, on_phone_pct, sleepy_pct,
                    distraction_episodes, main_cause, payload
                ) VALUES (
                    $1, $2, $3, $4,
                    to_timestamp($5), to_timestamp($6), $7,
                    $8, $9, $10, $11,
                    $12, $13, $14
                )
                """,
                anonymous_id,
                email,
                display_name,
                consent_given,
                started_at,
                ended_at,
                duration_s,
                _f(analysis.get("focused_pct")),
                _f(analysis.get("distracted_pct")),
                _f(analysis.get("on_phone_pct")),
                _f(analysis.get("sleepy_pct")),
                _i(analysis.get("distraction_episodes")),
                analysis.get("main_distraction_cause"),
                full_payload,
            )
    except Exception as e:
        logger.error(f"flush_session lỗi: {e}")


async def query_sessions(
    *,
    from_ts: Optional[float] = None,
    to_ts: Optional[float] = None,
    anonymous_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    if _pool is None:
        return []
    conditions: list[str] = []
    params: list[Any] = []
    idx = 1
    if from_ts is not None:
        conditions.append(f"started_at >= to_timestamp(${idx})")
        params.append(from_ts); idx += 1
    if to_ts is not None:
        conditions.append(f"started_at <= to_timestamp(${idx})")
        params.append(to_ts); idx += 1
    if anonymous_id is not None:
        conditions.append(f"anonymous_id = ${idx}")
        params.append(anonymous_id); idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
    SELECT id::text AS id,
           anonymous_id, email, display_name,
           extract(epoch from started_at)::float AS started_at,
           extract(epoch from ended_at)::float   AS ended_at,
           duration_s, focused_pct, distracted_pct, on_phone_pct, sleepy_pct,
           distraction_episodes, main_cause, payload
    FROM session_logs
    {where}
    ORDER BY started_at DESC
    """
    try:
        async with _pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"query_sessions lỗi: {e}")
        return []


def _f(v: Any) -> Optional[float]:
    return float(v) if v is not None else None


def _i(v: Any) -> Optional[int]:
    return int(v) if v is not None else None
