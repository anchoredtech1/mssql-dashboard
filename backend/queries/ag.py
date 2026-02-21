"""
queries/ag.py
Availability Group monitoring queries.
Covers: replica roles, sync state, redo/send queue lag, failover mode.
"""

import pyodbc
import logging

logger = logging.getLogger(__name__)


def get_ag_overview(conn: pyodbc.Connection) -> list:
    """
    Returns one row per AG replica with full health details.
    Run against the PRIMARY or any replica — results filtered by what's visible.
    """
    sql = """
    SELECT
        ag.name                                 AS ag_name,
        ar.replica_server_name,
        ar.availability_mode_desc               AS availability_mode,
        ar.failover_mode_desc                   AS failover_mode,
        ar.endpoint_url,
        ars.role_desc                           AS role,
        ars.operational_state_desc              AS operational_state,
        ars.connected_state_desc                AS connected_state,
        ars.synchronization_health_desc         AS sync_health,
        drs.synchronization_state_desc          AS sync_state,
        drs.database_state_desc                 AS database_state,
        drs.is_local,
        drs.is_primary_replica,
        drs.is_commit_participant,
        drs.synchronization_health_desc         AS db_sync_health,
        drs.log_send_queue_size                 AS log_send_queue_kb,
        drs.log_send_rate                       AS log_send_rate_kb_sec,
        drs.redo_queue_size                     AS redo_queue_kb,
        drs.redo_rate                           AS redo_rate_kb_sec,
        drs.last_hardened_lsn,
        drs.last_hardened_time,
        drs.last_received_time,
        drs.last_sent_time,
        drs.last_commit_time,
        drs.secondary_lag_seconds,
        DB_NAME(drs.database_id)                AS database_name
    FROM sys.availability_groups ag
    JOIN sys.availability_replicas ar
        ON ag.group_id = ar.group_id
    JOIN sys.dm_hadr_availability_replica_states ars
        ON ar.replica_id = ars.replica_id
    LEFT JOIN sys.dm_hadr_database_replica_states drs
        ON ar.replica_id = drs.replica_id
    ORDER BY ag.name, ar.replica_server_name, database_name;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [c[0] for c in cursor.description]
        rows = []
        for row in cursor.fetchall():
            d = dict(zip(cols, row))
            # Convert datetime objects to strings for JSON serialization
            for k, v in d.items():
                if hasattr(v, 'isoformat'):
                    d[k] = v.isoformat()
            rows.append(d)
        return rows
    except Exception as exc:
        logger.warning(f"get_ag_overview error: {exc}")
        return []


def get_ag_listener_info(conn: pyodbc.Connection) -> list:
    """
    Returns AG listener names, IPs, and ports.
    """
    sql = """
    SELECT
        ag.name             AS ag_name,
        l.dns_name          AS listener_name,
        l.port,
        l.ip_configuration_string_from_cluster,
        li.ip_address,
        li.ip_subnet_mask,
        li.network_subnet_ip,
        li.state_desc
    FROM sys.availability_group_listeners l
    JOIN sys.availability_groups ag ON l.group_id = ag.group_id
    LEFT JOIN sys.availability_group_listener_ip_addresses li
        ON l.listener_id = li.listener_id
    ORDER BY ag.name, l.dns_name;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    except Exception as exc:
        logger.warning(f"get_ag_listener_info error: {exc}")
        return []


def get_ag_failover_history(conn: pyodbc.Connection, days: int = 30) -> list:
    """
    Queries the SQL Server error log for AG failover events.
    Returns recent role change records from the default trace if available,
    or from msdb.dbo.suspect_pages as a fallback indicator.
    
    Note: True failover history requires reading Windows Event Log or
    extended events. This pulls from sys.fn_xe_file_target_read_file
    if an AlwaysOn_health session exists.
    """
    sql = """
    -- Check if AlwaysOn_health XE session data is available
    SELECT TOP 50
        event_data.value('(event/@timestamp)[1]', 'datetime2')   AS event_time,
        event_data.value('(event/data[@name="availability_group_name"]/value)[1]', 'nvarchar(256)')
            AS ag_name,
        event_data.value('(event/data[@name="previous_state"]/text)[1]', 'nvarchar(60)')
            AS previous_state,
        event_data.value('(event/data[@name="current_state"]/text)[1]', 'nvarchar(60)')
            AS current_state
    FROM (
        SELECT CAST(event_data AS XML) AS event_data
        FROM sys.fn_xe_file_target_read_file(
            N'AlwaysOn*.xel', NULL, NULL, NULL
        )
    ) AS xe_data
    WHERE event_data.value('(event/@name)[1]', 'nvarchar(256)')
          IN ('availability_replica_state_change', 'availability_replica_manager_state_change')
    ORDER BY event_time DESC;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [c[0] for c in cursor.description]
        rows = []
        for row in cursor.fetchall():
            d = dict(zip(cols, row))
            if d.get("event_time") and hasattr(d["event_time"], 'isoformat'):
                d["event_time"] = d["event_time"].isoformat()
            rows.append(d)
        return rows
    except Exception as exc:
        # XE session may not exist — return empty with note
        logger.info(f"get_ag_failover_history: XE data unavailable ({exc})")
        return []


def get_ag_summary(conn: pyodbc.Connection) -> dict:
    """
    Returns a high-level AG health summary: counts of healthy/unhealthy replicas.
    Used for the dashboard summary card.
    """
    rows = get_ag_overview(conn)
    if not rows:
        return {"has_ag": False, "groups": []}

    groups: dict = {}
    for row in rows:
        gname = row["ag_name"]
        if gname not in groups:
            groups[gname] = {
                "ag_name":    gname,
                "replicas":   [],
                "healthy":    True,
                "primary":    None,
            }
        groups[gname]["replicas"].append(row)
        if row.get("role") == "PRIMARY":
            groups[gname]["primary"] = row["replica_server_name"]
        if row.get("sync_health") not in ("HEALTHY", None):
            groups[gname]["healthy"] = False

    return {"has_ag": True, "groups": list(groups.values())}
