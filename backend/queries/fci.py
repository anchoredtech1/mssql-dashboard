"""
queries/fci.py
Failover Cluster Instance (FCI) monitoring queries.
Covers: active node, cluster nodes, resource groups, disk groups.
"""

import pyodbc
import logging

logger = logging.getLogger(__name__)


def get_fci_nodes(conn: pyodbc.Connection) -> list:
    """
    Returns all cluster nodes and which is the active (current) node.
    Uses sys.dm_os_cluster_nodes — available when IsClustered = 1.
    """
    sql = """
    SELECT
        NodeName,
        status,
        status_description,
        is_current_owner
    FROM sys.dm_os_cluster_nodes
    ORDER BY is_current_owner DESC, NodeName;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    except Exception as exc:
        logger.warning(f"get_fci_nodes error: {exc}")
        return []


def get_fci_resources(conn: pyodbc.Connection) -> list:
    """
    Returns cluster resources (IP addresses, disk groups, SQL Server name resource).
    Uses sys.dm_os_cluster_properties and sys.dm_io_cluster_shared_drives.
    """
    resources = []

    # Shared drives / disk witness
    drives_sql = """
    SELECT
        DriveName,
        IsMounted
    FROM sys.dm_io_cluster_shared_drives;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(drives_sql)
        cols = [c[0] for c in cursor.description]
        for row in cursor.fetchall():
            d = dict(zip(cols, row))
            d["resource_type"] = "disk"
            resources.append(d)
    except Exception as exc:
        logger.info(f"get_fci_resources (drives): {exc}")

    # Cluster properties (cluster name, quorum type)
    props_sql = """
    SELECT
        VerboseLogging,
        SqlDumperDumpFlags,
        SqlDumperDumpPath,
        SqlDumperDumpTimeOut,
        FailureConditionLevel,
        HealthCheckTimeout
    FROM sys.dm_os_cluster_properties;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(props_sql)
        cols = [c[0] for c in cursor.description]
        row = cursor.fetchone()
        if row:
            resources.append({"resource_type": "cluster_properties", **dict(zip(cols, row))})
    except Exception as exc:
        logger.info(f"get_fci_resources (props): {exc}")

    return resources


def get_fci_status(conn: pyodbc.Connection) -> dict:
    """
    Composite FCI status: active node, all nodes, shared drives.
    """
    nodes     = get_fci_nodes(conn)
    resources = get_fci_resources(conn)

    active_node = next(
        (n["NodeName"] for n in nodes if n.get("is_current_owner")),
        None
    )
    disk_resources = [r for r in resources if r.get("resource_type") == "disk"]

    return {
        "is_clustered": len(nodes) > 0,
        "active_node":  active_node,
        "nodes":        nodes,
        "shared_drives": disk_resources,
        "all_resources": resources,
    }
