"""
queries/health.py
Core server health queries: CPU, memory, sessions, wait stats, top queries.
All functions accept a pyodbc connection and return plain dicts.
"""

import pyodbc
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── CPU & Memory ─────────────────────────────────────────────────────────────

def get_cpu_memory(conn: pyodbc.Connection) -> dict:
    """
    Returns SQL Server CPU usage and buffer pool memory stats.
    Uses sys.dm_os_ring_buffers for CPU (works on all editions).
    """
    sql = """
    -- CPU: most recent ring buffer sample
    SELECT TOP 1
        100 - SystemIdle AS sql_cpu_percent,
        SQLProcessUtilization AS sqlserver_cpu_percent
    FROM (
        SELECT
            record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int')
                AS SQLProcessUtilization,
            record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]', 'int')
                AS SystemIdle
        FROM (
            SELECT TOP 1 CONVERT(XML, record) AS record
            FROM sys.dm_os_ring_buffers
            WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR'
              AND record LIKE '%%<SystemHealth>%%'
            ORDER BY timestamp DESC
        ) AS ring
    ) AS cpu_data;
    """
    mem_sql = """
    SELECT
        physical_memory_in_use_kb / 1024.0    AS memory_used_mb,
        page_fault_count,
        memory_utilization_percentage
    FROM sys.dm_os_process_memory;
    """
    total_mem_sql = """
    SELECT physical_memory_kb / 1024.0 AS total_physical_mb
    FROM sys.dm_os_sys_info;
    """

    result = {"cpu_percent": None, "memory_used_mb": None, "memory_total_mb": None}

    try:
        cursor = conn.cursor()

        cursor.execute(sql)
        row = cursor.fetchone()
        if row:
            result["cpu_percent"] = float(row[0]) if row[0] is not None else None

        cursor.execute(mem_sql)
        row = cursor.fetchone()
        if row:
            result["memory_used_mb"] = round(float(row[0]), 1) if row[0] else None

        cursor.execute(total_mem_sql)
        row = cursor.fetchone()
        if row:
            result["memory_total_mb"] = round(float(row[0]), 1) if row[0] else None

    except Exception as exc:
        logger.warning(f"get_cpu_memory error: {exc}")
        result["error"] = str(exc)

    return result


# ── Sessions ──────────────────────────────────────────────────────────────────

def get_sessions(conn: pyodbc.Connection) -> dict:
    """
    Returns active session count, blocked session count, and blocked session details.
    """
    sql = """
    SELECT
        COUNT(*)                                          AS total_active,
        SUM(CASE WHEN blocking_session_id > 0 THEN 1 ELSE 0 END) AS blocked_count
    FROM sys.dm_exec_sessions s
    JOIN sys.dm_exec_requests r ON s.session_id = r.session_id
    WHERE s.is_user_process = 1;
    """
    blocked_sql = """
    SELECT TOP 20
        r.session_id,
        r.blocking_session_id,
        r.wait_type,
        r.wait_time / 1000.0            AS wait_seconds,
        r.status,
        DB_NAME(r.database_id)          AS database_name,
        SUBSTRING(
            st.text,
            (r.statement_start_offset/2)+1,
            CASE r.statement_end_offset
                WHEN -1 THEN DATALENGTH(st.text)
                ELSE r.statement_end_offset
            END - r.statement_start_offset
        ) / 2 + 1                       AS current_sql,
        s.login_name,
        s.host_name,
        s.program_name,
        r.cpu_time,
        r.logical_reads
    FROM sys.dm_exec_requests r
    JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
    CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) st
    WHERE r.blocking_session_id > 0
      AND s.is_user_process = 1
    ORDER BY r.wait_time DESC;
    """

    result = {"active_sessions": 0, "blocked_sessions": 0, "blocked_details": []}

    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        row = cursor.fetchone()
        if row:
            result["active_sessions"]  = int(row[0]) if row[0] else 0
            result["blocked_sessions"] = int(row[1]) if row[1] else 0

        if result["blocked_sessions"] > 0:
            cursor.execute(blocked_sql)
            cols = [c[0] for c in cursor.description]
            result["blocked_details"] = [
                dict(zip(cols, r)) for r in cursor.fetchall()
            ]
    except Exception as exc:
        logger.warning(f"get_sessions error: {exc}")
        result["error"] = str(exc)

    return result


# ── Wait Stats ────────────────────────────────────────────────────────────────

def get_wait_stats(conn: pyodbc.Connection, top_n: int = 10) -> list:
    """
    Returns the top N wait types by total wait time (since last clear/restart).
    Filters out benign background waits.
    """
    sql = f"""
    SELECT TOP {top_n}
        wait_type,
        waiting_tasks_count,
        wait_time_ms,
        max_wait_time_ms,
        signal_wait_time_ms,
        wait_time_ms - signal_wait_time_ms AS resource_wait_ms
    FROM sys.dm_os_wait_stats
    WHERE wait_type NOT IN (
        'SLEEP_TASK','BROKER_TO_FLUSH','BROKER_TASK_STOP','CLR_AUTO_EVENT',
        'DISPATCHER_QUEUE_SEMAPHORE','FT_IFTS_SCHEDULER_IDLE_WAIT',
        'HADR_CLUSAPI_CALL','HADR_FILESTREAM_IOMGR_IOCOMPLETION',
        'HADR_WORK_QUEUE','LAZYWRITER_SLEEP','LOGMGR_QUEUE',
        'ONDEMAND_TASK_QUEUE','REQUEST_FOR_DEADLOCK_SEARCH',
        'RESOURCE_QUEUE','SERVER_IDLE_CHECK','SLEEP_DBSTARTUP',
        'SLEEP_DBTASK','SLEEP_MASTERDBREADY','SLEEP_MASTERMDREADY',
        'SLEEP_MASTERUPGRADED','SLEEP_MSDBSTARTUP','SLEEP_SYSTEMTASK',
        'SLEEP_TEMPDBSTARTUP','SNI_HTTP_ACCEPT','SP_SERVER_DIAGNOSTICS_SLEEP',
        'SQLTRACE_BUFFER_FLUSH','SQLTRACE_INCREMENTAL_FLUSH_SLEEP',
        'WAIT_XTP_OFFLINE_CKPT_NEW_LOG','WAITFOR',
        'XE_DISPATCHER_WAIT','XE_TIMER_EVENT','BROKER_EVENTHANDLER',
        'CHECKPOINT_QUEUE','DBMIRROR_EVENTS_QUEUE','SQLTRACE_WAIT_ENTRIES',
        'WAIT_XTP_ONLINE_CKPT_COMPLETE','XE_DISPATCHER_JOIN',
        'BROKER_RECEIVE_WAITFOR'
    )
    ORDER BY wait_time_ms DESC;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    except Exception as exc:
        logger.warning(f"get_wait_stats error: {exc}")
        return []


# ── Database List ─────────────────────────────────────────────────────────────

def get_databases(conn: pyodbc.Connection) -> list:
    """
    Returns all user databases with state, recovery model, and size.
    """
    sql = """
    SELECT
        d.database_id,
        d.name,
        d.state_desc,
        d.recovery_model_desc,
        d.log_reuse_wait_desc,
        d.is_read_only,
        d.is_in_standby,
        ISNULL(SUM(mf.size) * 8 / 1024.0, 0) AS size_mb
    FROM sys.databases d
    LEFT JOIN sys.master_files mf ON d.database_id = mf.database_id
    WHERE d.database_id > 4   -- exclude system DBs (master/model/msdb/tempdb)
    GROUP BY
        d.database_id, d.name, d.state_desc, d.recovery_model_desc,
        d.log_reuse_wait_desc, d.is_read_only, d.is_in_standby
    ORDER BY d.name;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    except Exception as exc:
        logger.warning(f"get_databases error: {exc}")
        return []


# ── Server Properties ─────────────────────────────────────────────────────────

def get_server_properties(conn: pyodbc.Connection) -> dict:
    """
    Returns key server properties: edition, version, uptime, collation.
    """
    sql = """
    SELECT
        SERVERPROPERTY('ServerName')         AS server_name,
        SERVERPROPERTY('Edition')            AS edition,
        SERVERPROPERTY('ProductVersion')     AS version,
        SERVERPROPERTY('ProductLevel')       AS product_level,
        SERVERPROPERTY('ProductUpdateLevel') AS update_level,
        SERVERPROPERTY('Collation')          AS collation,
        SERVERPROPERTY('IsClustered')        AS is_clustered,
        SERVERPROPERTY('IsHadrEnabled')      AS hadr_enabled,
        sqlserver_start_time
    FROM sys.dm_os_sys_info;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [c[0] for c in cursor.description]
        row  = cursor.fetchone()
        if row:
            data = dict(zip(cols, row))
            # Convert sqlserver_start_time to string for JSON
            if data.get("sqlserver_start_time"):
                data["sqlserver_start_time"] = str(data["sqlserver_start_time"])
            return data
    except Exception as exc:
        logger.warning(f"get_server_properties error: {exc}")
    return {}


# ── Composite health snapshot ─────────────────────────────────────────────────

def get_full_health(conn: pyodbc.Connection) -> dict:
    """
    Run all health queries in one call and return a combined dict.
    Used by the scheduler to store periodic snapshots.
    """
    cpu_mem  = get_cpu_memory(conn)
    sessions = get_sessions(conn)
    waits    = get_wait_stats(conn, top_n=10)
    props    = get_server_properties(conn)
    dbs      = get_databases(conn)

    total_wait = sum(w.get("wait_time_ms", 0) for w in waits) if waits else 0

    return {
        "cpu_percent":      cpu_mem.get("cpu_percent"),
        "memory_used_mb":   cpu_mem.get("memory_used_mb"),
        "memory_total_mb":  cpu_mem.get("memory_total_mb"),
        "active_sessions":  sessions.get("active_sessions", 0),
        "blocked_sessions": sessions.get("blocked_sessions", 0),
        "blocked_details":  sessions.get("blocked_details", []),
        "total_wait_ms":    total_wait,
        "top_waits":        waits,
        "server_props":     props,
        "databases":        dbs,
    }
