"""
queries/log_shipping.py
Log shipping monitoring — reads from msdb.dbo.log_shipping_* tables.
Works for: primary server, secondary server, or a dedicated monitor server.
"""

import pyodbc
import logging

logger = logging.getLogger(__name__)


def get_log_shipping_primaries(conn: pyodbc.Connection) -> list:
    """
    Returns log shipping primary database configurations and last backup info.
    Run against the PRIMARY or MONITOR server.
    """
    sql = """
    SELECT
        p.primary_server,
        p.primary_database,
        p.backup_directory,
        p.backup_share,
        p.backup_retention_period,
        p.backup_threshold,
        p.threshold_alert_enabled,
        p.last_backup_file,
        p.last_backup_date,
        p.last_backup_date_utc,
        p.history_retention_period,
        s.secondary_server,
        s.secondary_database,
        s.last_copied_file,
        s.last_copied_date,
        s.last_copied_date_utc
    FROM msdb.dbo.log_shipping_monitor_primary p
    LEFT JOIN msdb.dbo.log_shipping_monitor_secondary s
        ON p.primary_server = s.primary_server
        AND p.primary_database = s.primary_database
    ORDER BY p.primary_database, s.secondary_server;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [c[0] for c in cursor.description]
        rows = []
        for row in cursor.fetchall():
            d = dict(zip(cols, row))
            for k, v in d.items():
                if hasattr(v, 'isoformat'):
                    d[k] = v.isoformat()
            rows.append(d)
        return rows
    except Exception as exc:
        logger.warning(f"get_log_shipping_primaries error: {exc}")
        return []


def get_log_shipping_secondaries(conn: pyodbc.Connection) -> list:
    """
    Returns log shipping secondary configuration and restore status.
    Run against the SECONDARY server.
    """
    sql = """
    SELECT
        s.primary_server,
        s.primary_database,
        s.secondary_server       = @@SERVERNAME,
        s.secondary_database,
        s.restore_delay,
        s.restore_mode,
        s.disconnect_users,
        s.restore_threshold,
        s.threshold_alert_enabled,
        s.last_copied_file,
        s.last_copied_date,
        s.last_restored_file,
        s.last_restored_date,
        s.last_restored_latency,  -- minutes between log backup and restore
        s.history_retention_period
    FROM msdb.dbo.log_shipping_monitor_secondary s
    ORDER BY s.primary_database;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [c[0] for c in cursor.description]
        rows = []
        for row in cursor.fetchall():
            d = dict(zip(cols, row))
            for k, v in d.items():
                if hasattr(v, 'isoformat'):
                    d[k] = v.isoformat()
            rows.append(d)
        return rows
    except Exception as exc:
        logger.warning(f"get_log_shipping_secondaries error: {exc}")
        return []


def get_log_shipping_alerts(conn: pyodbc.Connection) -> list:
    """
    Checks for out-of-threshold log shipping conditions by comparing
    last_backup_date / last_restored_date against configured thresholds.
    Returns a list of alert dicts for any databases in violation.
    """
    sql = """
    SELECT
        p.primary_server,
        p.primary_database,
        s.secondary_server,
        s.secondary_database,
        p.backup_threshold,         -- minutes
        p.last_backup_date,
        s.restore_threshold,        -- minutes
        s.last_restored_date,
        s.last_restored_latency,
        -- Minutes since last backup
        DATEDIFF(MINUTE, p.last_backup_date, GETDATE())   AS minutes_since_backup,
        -- Minutes since last restore
        DATEDIFF(MINUTE, s.last_restored_date, GETDATE()) AS minutes_since_restore
    FROM msdb.dbo.log_shipping_monitor_primary p
    JOIN msdb.dbo.log_shipping_monitor_secondary s
        ON p.primary_server   = s.primary_server
        AND p.primary_database = s.primary_database
    ORDER BY p.primary_database;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [c[0] for c in cursor.description]
        alerts = []
        for row in cursor.fetchall():
            d = dict(zip(cols, row))
            for k, v in d.items():
                if hasattr(v, 'isoformat'):
                    d[k] = v.isoformat()

            # Evaluate threshold violations
            backup_threshold  = d.get("backup_threshold") or 60
            restore_threshold = d.get("restore_threshold") or 45
            mins_backup  = d.get("minutes_since_backup")
            mins_restore = d.get("minutes_since_restore")

            d["backup_status"]  = "ok"
            d["restore_status"] = "ok"

            if mins_backup is not None and mins_backup > backup_threshold:
                d["backup_status"] = "warning" if mins_backup < backup_threshold * 2 else "critical"

            if mins_restore is not None and mins_restore > restore_threshold:
                d["restore_status"] = "warning" if mins_restore < restore_threshold * 2 else "critical"

            d["out_of_sync"] = d["backup_status"] != "ok" or d["restore_status"] != "ok"
            alerts.append(d)
        return alerts
    except Exception as exc:
        logger.warning(f"get_log_shipping_alerts error: {exc}")
        return []


def get_log_shipping_summary(conn: pyodbc.Connection) -> dict:
    """
    Composite view: primaries + secondaries + alert status.
    """
    primaries   = get_log_shipping_primaries(conn)
    secondaries = get_log_shipping_secondaries(conn)
    alerts      = get_log_shipping_alerts(conn)
    out_of_sync = [a for a in alerts if a.get("out_of_sync")]

    return {
        "has_log_shipping": len(primaries) > 0 or len(secondaries) > 0,
        "primaries":        primaries,
        "secondaries":      secondaries,
        "alerts":           alerts,
        "out_of_sync_count": len(out_of_sync),
        "out_of_sync":      out_of_sync,
    }
