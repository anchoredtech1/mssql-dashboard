"""
connections/builder.py
Builds pyodbc connection strings for all supported auth types:
  - SQL Server Authentication (username + password)
  - Windows / Integrated Authentication
  - TLS/SSL + Certificate (for encrypted servers incl. AWS-connected)
"""

import os
from typing import Optional
from database import MonitoredServer, AuthType


# Prefer the ODBC 18 driver, fall back to 17 if not installed
_DRIVER_PREFERENCE = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "SQL Server",
]


def get_odbc_driver() -> str:
    """Return the best available ODBC driver name."""
    try:
        import pyodbc
        installed = [d for d in pyodbc.drivers() if "SQL Server" in d]
        for preferred in _DRIVER_PREFERENCE:
            if preferred in installed:
                return preferred
        if installed:
            return installed[0]
    except Exception:
        pass
    return "ODBC Driver 18 for SQL Server"   # default – let it fail with a clear message


def build_connection_string(server: MonitoredServer, decrypted_password: Optional[str] = None) -> str:
    """
    Build a pyodbc connection string for the given server record.

    Args:
        server:             ORM model from monitored_servers table
        decrypted_password: Already-decrypted password (crypto.decrypt called by caller)

    Returns:
        Full ODBC connection string
    """
    driver = get_odbc_driver()

    # Build host/instance part
    host = server.host
    if server.instance_name:
        host = f"{host}\\{server.instance_name}"
    if server.port and server.port != 1433:
        host = f"{host},{server.port}"

    parts: dict = {
        "Driver":  f"{{{driver}}}",
        "Server":  host,
        "Database": "master",         # connect to master; queries specify DB
        "Connection Timeout": "10",
    }

    # ── Auth type ────────────────────────────────────────────────────────────
    if server.auth_type == AuthType.sql:
        from crypto import decrypt
        username = decrypt(server.username) if server.username else ""
        password = decrypted_password or (decrypt(server.password) if server.password else "")
        parts["UID"] = username
        parts["PWD"] = password
        parts["Trusted_Connection"] = "no"

    elif server.auth_type == AuthType.windows:
        parts["Trusted_Connection"] = "yes"
        # Remove UID/PWD – Windows auth uses the service account or current user
        parts.pop("UID", None)
        parts.pop("PWD", None)

    elif server.auth_type == AuthType.tls_cert:
        from crypto import decrypt
        username = decrypt(server.username) if server.username else ""
        password = decrypted_password or (decrypt(server.password) if server.password else "")
        if username:
            parts["UID"] = username
        if password:
            parts["PWD"] = password
        parts["Trusted_Connection"] = "no"
        parts["Encrypt"] = "yes"
        parts["TrustServerCertificate"] = "no"
        # Certificate path for servers with custom CA (AWS RDS, etc.)
        if server.cert_path and os.path.isfile(server.cert_path):
            parts["ServerCertificate"] = server.cert_path

    # ── Global TLS override ──────────────────────────────────────────────────
    if server.encrypt and server.auth_type != AuthType.tls_cert:
        parts["Encrypt"] = "yes"
        parts["TrustServerCertificate"] = "yes" if server.trust_cert else "no"

    return ";".join(f"{k}={v}" for k, v in parts.items())


def build_sqlalchemy_url(server: MonitoredServer) -> str:
    """
    Build a SQLAlchemy connection URL using the pyodbc connection string.
    Used for SQLAlchemy engine creation if needed.
    """
    import urllib.parse
    conn_str = build_connection_string(server)
    return "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(conn_str)
