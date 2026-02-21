"""
routers/clusters.py
Cluster health endpoints: Availability Groups + FCI + Log Shipping.

GET /clusters/{server_id}/ag              – AG overview (all replicas)
GET /clusters/{server_id}/ag/summary      – AG summary card
GET /clusters/{server_id}/ag/listeners    – AG listener info
GET /clusters/{server_id}/ag/failover     – AG failover history
GET /clusters/{server_id}/fci             – FCI node + disk status
GET /clusters/{server_id}/logshipping     – Log shipping summary
GET /clusters/{server_id}/logshipping/alerts – Out-of-threshold alert rows
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, MonitoredServer
from connections.manager import pool
from queries.ag import get_ag_overview, get_ag_summary, get_ag_listener_info, get_ag_failover_history
from queries.fci import get_fci_status
from queries.log_shipping import get_log_shipping_summary, get_log_shipping_alerts

router = APIRouter(prefix="/clusters", tags=["clusters"])


def _get_live_conn(server_id: int, db: Session):
    srv = db.query(MonitoredServer).filter(
        MonitoredServer.id == server_id,
        MonitoredServer.enabled == True
    ).first()
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found or disabled")
    try:
        return pool.get_connection(srv)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot connect to server: {exc}")


# ── Availability Groups ───────────────────────────────────────────────────────

@router.get("/{server_id}/ag")
def ag_detail(server_id: int, db: Session = Depends(get_db)):
    conn = _get_live_conn(server_id, db)
    return get_ag_overview(conn)


@router.get("/{server_id}/ag/summary")
def ag_summary(server_id: int, db: Session = Depends(get_db)):
    conn = _get_live_conn(server_id, db)
    return get_ag_summary(conn)


@router.get("/{server_id}/ag/listeners")
def ag_listeners(server_id: int, db: Session = Depends(get_db)):
    conn = _get_live_conn(server_id, db)
    return get_ag_listener_info(conn)


@router.get("/{server_id}/ag/failover")
def ag_failover_history(server_id: int, days: int = 30, db: Session = Depends(get_db)):
    conn = _get_live_conn(server_id, db)
    return get_ag_failover_history(conn, days=days)


# ── Failover Cluster Instances ────────────────────────────────────────────────

@router.get("/{server_id}/fci")
def fci_status(server_id: int, db: Session = Depends(get_db)):
    conn = _get_live_conn(server_id, db)
    return get_fci_status(conn)


# ── Log Shipping ──────────────────────────────────────────────────────────────

@router.get("/{server_id}/logshipping")
def log_shipping_summary(server_id: int, db: Session = Depends(get_db)):
    conn = _get_live_conn(server_id, db)
    return get_log_shipping_summary(conn)


@router.get("/{server_id}/logshipping/alerts")
def log_shipping_alerts(server_id: int, db: Session = Depends(get_db)):
    conn = _get_live_conn(server_id, db)
    return get_log_shipping_alerts(conn)
