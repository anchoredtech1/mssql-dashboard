"""
routers/metrics.py
Live metric endpoints — called by the frontend dashboard.

GET /metrics/{server_id}/health       – full health snapshot (live)
GET /metrics/{server_id}/sessions     – active & blocked sessions
GET /metrics/{server_id}/waits        – top wait stats
GET /metrics/{server_id}/databases    – database list
GET /metrics/{server_id}/history      – stored metric snapshots
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from database import get_db, MonitoredServer, MetricSnapshot
from connections.manager import pool
from queries.health import get_full_health, get_sessions, get_wait_stats, get_databases

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _get_live_conn(server_id: int, db: Session):
    """Helper: fetch the server record and return a live connection."""
    srv = db.query(MonitoredServer).filter(
        MonitoredServer.id == server_id,
        MonitoredServer.enabled == True
    ).first()
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found or disabled")
    try:
        conn = pool.get_connection(srv)
        return conn
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot connect to server: {exc}")


@router.get("/{server_id}/health")
def health_snapshot(server_id: int, db: Session = Depends(get_db)):
    conn = _get_live_conn(server_id, db)
    data = get_full_health(conn)
    data["server_id"]   = server_id
    data["captured_at"] = datetime.utcnow().isoformat()
    return data


@router.get("/{server_id}/sessions")
def sessions(server_id: int, db: Session = Depends(get_db)):
    conn = _get_live_conn(server_id, db)
    return get_sessions(conn)


@router.get("/{server_id}/waits")
def wait_stats(server_id: int, top: int = 10, db: Session = Depends(get_db)):
    conn = _get_live_conn(server_id, db)
    return get_wait_stats(conn, top_n=min(top, 25))


@router.get("/{server_id}/databases")
def databases(server_id: int, db: Session = Depends(get_db)):
    conn = _get_live_conn(server_id, db)
    return get_databases(conn)


@router.get("/{server_id}/history")
def metric_history(
    server_id: int,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Returns stored metric snapshots from SQLite for charting.
    """
    since = datetime.utcnow() - timedelta(hours=min(hours, 168))  # max 7 days
    snapshots = (
        db.query(MetricSnapshot)
        .filter(
            MetricSnapshot.server_id == server_id,
            MetricSnapshot.captured_at >= since
        )
        .order_by(MetricSnapshot.captured_at.asc())
        .limit(2000)
        .all()
    )
    return [
        {
            "captured_at":      s.captured_at.isoformat(),
            "cpu_percent":      s.cpu_percent,
            "memory_used_mb":   s.memory_used_mb,
            "active_sessions":  s.active_sessions,
            "blocked_sessions": s.blocked_sessions,
            "status":           s.status,
        }
        for s in snapshots
    ]
