"""
connections/manager.py
Thread-safe connection pool manager.
Keeps one persistent pyodbc connection per server, reconnects on failure.
"""

import pyodbc
import threading
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from connections.builder import build_connection_string
from database import MonitoredServer

logger = logging.getLogger(__name__)

# How long a healthy connection is trusted before we re-test it
_CONN_MAX_AGE_SECONDS = 300


class _PoolEntry:
    def __init__(self, conn: pyodbc.Connection, conn_str: str):
        self.conn      = conn
        self.conn_str  = conn_str
        self.created   = datetime.utcnow()
        self.last_used = datetime.utcnow()
        self.lock      = threading.Lock()

    def is_stale(self) -> bool:
        return (datetime.utcnow() - self.created).total_seconds() > _CONN_MAX_AGE_SECONDS


class ConnectionManager:
    """Singleton-style manager; import the module-level `pool` instance."""

    def __init__(self):
        self._pool: Dict[int, _PoolEntry] = {}
        self._global_lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def get_connection(self, server: MonitoredServer) -> pyodbc.Connection:
        """
        Return a live pyodbc connection for the given server.
        Reconnects automatically if the connection is stale or broken.
        """
        with self._global_lock:
            entry = self._pool.get(server.id)

        if entry is not None:
            with entry.lock:
                if not entry.is_stale() and self._is_alive(entry.conn):
                    entry.last_used = datetime.utcnow()
                    return entry.conn
                # Stale or dead — close and reconnect
                self._close_entry(entry)

        # Build a fresh connection
        conn_str = build_connection_string(server)
        conn = self._connect(conn_str)
        entry = _PoolEntry(conn, conn_str)

        with self._global_lock:
            self._pool[server.id] = entry

        return conn

    def test_connection(self, server: MonitoredServer) -> dict:
        """
        Attempt a connection and return a result dict.
        Does NOT store the connection in the pool.
        """
        try:
            conn_str = build_connection_string(server)
            conn = pyodbc.connect(conn_str, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT @@SERVERNAME, @@VERSION")
            row = cursor.fetchone()
            conn.close()
            return {
                "success": True,
                "server_name": row[0] if row else None,
                "version": (row[1] or "")[:120] if row else None,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def remove(self, server_id: int) -> None:
        """Remove and close a server's connection from the pool."""
        with self._global_lock:
            entry = self._pool.pop(server_id, None)
        if entry:
            with entry.lock:
                self._close_entry(entry)

    def close_all(self) -> None:
        """Shut down all connections (called on app shutdown)."""
        with self._global_lock:
            entries = list(self._pool.values())
            self._pool.clear()
        for entry in entries:
            with entry.lock:
                self._close_entry(entry)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _connect(conn_str: str) -> pyodbc.Connection:
        conn = pyodbc.connect(conn_str, timeout=10, autocommit=True)
        conn.timeout = 30   # query timeout
        return conn

    @staticmethod
    def _is_alive(conn: pyodbc.Connection) -> bool:
        try:
            conn.cursor().execute("SELECT 1")
            return True
        except Exception:
            return False

    @staticmethod
    def _close_entry(entry: _PoolEntry) -> None:
        try:
            entry.conn.close()
        except Exception:
            pass


# Module-level singleton – import this in query modules
pool = ConnectionManager()
