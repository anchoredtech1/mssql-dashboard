"""
scheduler.py
APScheduler background jobs — poll all enabled servers on their configured interval,
store snapshots in SQLite, evaluate alert rules.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler = None


def _poll_server(server_id: int):
    """
    Single server poll job: collect health metrics, store snapshot, fire alerts.
    Runs in a background thread — each call gets its own DB session.
    """
    from database import SessionLocal, MonitoredServer, MetricSnapshot, AlertRule, AlertEvent, AlertSeverity
    from connections.manager import pool
    from queries.health import get_full_health

    db = SessionLocal()
    try:
        srv = db.query(MonitoredServer).filter(
            MonitoredServer.id == server_id,
            MonitoredServer.enabled == True
        ).first()
        if not srv:
            return

        try:
            conn   = pool.get_connection(srv)
            health = get_full_health(conn)
            err    = None
            status = "ok"
        except Exception as exc:
            health = {}
            err    = str(exc)
            status = "error"
            logger.warning(f"Poll failed for server {server_id}: {exc}")

        # ── Store snapshot ────────────────────────────────────────────────────
        snap = MetricSnapshot(
            server_id        = server_id,
            captured_at      = datetime.utcnow(),
            cpu_percent      = health.get("cpu_percent"),
            memory_used_mb   = health.get("memory_used_mb"),
            memory_total_mb  = health.get("memory_total_mb"),
            active_sessions  = health.get("active_sessions"),
            blocked_sessions = health.get("blocked_sessions"),
            total_wait_ms    = health.get("total_wait_ms"),
            status           = status,
            error_message    = err,
        )
        db.add(snap)

        # ── Evaluate alert rules ──────────────────────────────────────────────
        if status == "ok":
            rules = db.query(AlertRule).filter(
                AlertRule.enabled == True,
                (AlertRule.server_id == server_id) | (AlertRule.server_id == None)
            ).all()

            metric_values = {
                "cpu_percent":      health.get("cpu_percent"),
                "memory_used_mb":   health.get("memory_used_mb"),
                "active_sessions":  health.get("active_sessions"),
                "blocked_sessions": health.get("blocked_sessions"),
                "total_wait_ms":    health.get("total_wait_ms"),
            }

            for rule in rules:
                value = metric_values.get(rule.metric)
                if value is None:
                    continue

                triggered = (
                    (rule.operator == "gt" and value > rule.threshold) or
                    (rule.operator == "lt" and value < rule.threshold) or
                    (rule.operator == "eq" and value == rule.threshold)
                )

                if triggered:
                    event = AlertEvent(
                        server_id = server_id,
                        rule_id   = rule.id,
                        fired_at  = datetime.utcnow(),
                        severity  = rule.severity,
                        metric    = rule.metric,
                        value     = float(value),
                        threshold = rule.threshold,
                        message   = (
                            f"{rule.metric} is {value} "
                            f"({'>' if rule.operator == 'gt' else '<'} {rule.threshold})"
                        ),
                    )
                    db.add(event)
                    logger.info(f"Alert fired: server={server_id} {event.message}")

        db.commit()

        # ── Prune old snapshots (keep 7 days) ────────────────────────────────
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=7)
        db.query(MetricSnapshot).filter(
            MetricSnapshot.server_id == server_id,
            MetricSnapshot.captured_at < cutoff
        ).delete()
        db.commit()

    finally:
        db.close()


def _refresh_jobs():
    """
    Re-sync scheduler jobs with current server list.
    Called at startup and whenever a server is added/edited.
    """
    global _scheduler
    if not _scheduler:
        return

    from database import SessionLocal, MonitoredServer
    db = SessionLocal()
    try:
        servers = db.query(MonitoredServer).filter(MonitoredServer.enabled == True).all()
        existing_ids = {int(j.id) for j in _scheduler.get_jobs()}
        server_ids   = {s.id for s in servers}

        # Add new jobs
        for srv in servers:
            job_id = str(srv.id)
            if srv.id not in existing_ids:
                _scheduler.add_job(
                    _poll_server,
                    trigger=IntervalTrigger(seconds=srv.poll_interval),
                    args=[srv.id],
                    id=job_id,
                    replace_existing=True,
                    misfire_grace_time=30,
                )
                logger.info(f"Scheduled polling for server {srv.id} ({srv.display_name}) every {srv.poll_interval}s")

        # Remove jobs for deleted/disabled servers
        for job in _scheduler.get_jobs():
            if int(job.id) not in server_ids:
                job.remove()
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler(
        job_defaults={"coalesce": True, "max_instances": 1},
        timezone="UTC"
    )
    _scheduler.start()
    _refresh_jobs()
    logger.info("APScheduler started")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")


def reschedule_server(server_id: int, poll_interval: int):
    """Call after updating a server's poll_interval."""
    global _scheduler
    if not _scheduler:
        return
    job_id = str(server_id)
    _scheduler.reschedule_job(
        job_id,
        trigger=IntervalTrigger(seconds=poll_interval)
    )
