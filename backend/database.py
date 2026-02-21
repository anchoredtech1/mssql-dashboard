"""
database.py – SQLite ORM models via SQLAlchemy
All credential fields are stored encrypted (see crypto.py)
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    Float, DateTime, Text, Enum as SAEnum
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import enum
import os

DB_PATH = os.environ.get("DB_PATH", "mssql_dashboard.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Enums ────────────────────────────────────────────────────────────────────

class AuthType(str, enum.Enum):
    sql       = "sql"        # SQL Server login (user + password)
    windows   = "windows"    # Windows / Integrated Auth
    tls_cert  = "tls_cert"   # Encrypted + certificate


class ServerRole(str, enum.Enum):
    standalone   = "standalone"
    fci          = "fci"
    ag_primary   = "ag_primary"
    ag_secondary = "ag_secondary"
    log_primary  = "log_primary"
    log_secondary = "log_secondary"
    log_monitor  = "log_monitor"


class AlertSeverity(str, enum.Enum):
    info     = "info"
    warning  = "warning"
    critical = "critical"


# ── Models ───────────────────────────────────────────────────────────────────

class MonitoredServer(Base):
    """Registry of all MSSQL servers/instances to monitor."""
    __tablename__ = "monitored_servers"

    id            = Column(Integer, primary_key=True, index=True)
    display_name  = Column(String(120), nullable=False)          # friendly label
    host          = Column(String(255), nullable=False)          # VNN, hostname, or IP
    port          = Column(Integer, default=1433)
    instance_name = Column(String(80), nullable=True)            # e.g. MSSQLSERVER
    auth_type     = Column(SAEnum(AuthType), nullable=False)
    username      = Column(Text, nullable=True)                  # encrypted
    password      = Column(Text, nullable=True)                  # encrypted
    cert_path     = Column(String(512), nullable=True)           # path to .cer/.pem
    encrypt       = Column(Boolean, default=False)               # force TLS
    trust_cert    = Column(Boolean, default=True)                # TrustServerCertificate
    role          = Column(SAEnum(ServerRole), default=ServerRole.standalone)
    cluster_name  = Column(String(120), nullable=True)           # group FCIs/AGs together
    enabled       = Column(Boolean, default=True)
    poll_interval = Column(Integer, default=60)                  # seconds
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes         = Column(Text, nullable=True)


class MetricSnapshot(Base):
    """Point-in-time health snapshot for a server."""
    __tablename__ = "metric_snapshots"

    id               = Column(Integer, primary_key=True, index=True)
    server_id        = Column(Integer, nullable=False, index=True)
    captured_at      = Column(DateTime, default=datetime.utcnow, index=True)
    cpu_percent      = Column(Float, nullable=True)
    memory_used_mb   = Column(Float, nullable=True)
    memory_total_mb  = Column(Float, nullable=True)
    active_sessions  = Column(Integer, nullable=True)
    blocked_sessions = Column(Integer, nullable=True)
    total_wait_ms    = Column(Float, nullable=True)
    status           = Column(String(20), default="ok")   # ok | warn | error
    error_message    = Column(Text, nullable=True)


class AGStatus(Base):
    """Availability Group replica status snapshot."""
    __tablename__ = "ag_status"

    id                    = Column(Integer, primary_key=True, index=True)
    server_id             = Column(Integer, nullable=False, index=True)
    captured_at           = Column(DateTime, default=datetime.utcnow, index=True)
    ag_name               = Column(String(128))
    replica_server_name   = Column(String(255))
    role                  = Column(String(20))          # PRIMARY / SECONDARY
    availability_mode     = Column(String(30))          # SYNCHRONOUS_COMMIT etc.
    failover_mode         = Column(String(20))          # AUTOMATIC / MANUAL
    synchronization_state = Column(String(30))          # SYNCHRONIZED / SYNCHRONIZING
    redo_queue_size_kb    = Column(Float, nullable=True)
    redo_rate_kb_sec      = Column(Float, nullable=True)
    log_send_queue_kb     = Column(Float, nullable=True)
    last_hardened_lsn     = Column(String(50), nullable=True)
    is_local              = Column(Boolean, default=False)


class FCIStatus(Base):
    """Failover Cluster Instance status snapshot."""
    __tablename__ = "fci_status"

    id             = Column(Integer, primary_key=True, index=True)
    server_id      = Column(Integer, nullable=False, index=True)
    captured_at    = Column(DateTime, default=datetime.utcnow, index=True)
    node_name      = Column(String(255))
    status         = Column(String(30))        # up / down / unknown
    is_current     = Column(Boolean, default=False)
    cluster_name   = Column(String(128), nullable=True)
    resource_group = Column(String(128), nullable=True)


class LogShippingStatus(Base):
    """Log shipping monitor table snapshot."""
    __tablename__ = "log_shipping_status"

    id                       = Column(Integer, primary_key=True, index=True)
    server_id                = Column(Integer, nullable=False, index=True)
    captured_at              = Column(DateTime, default=datetime.utcnow, index=True)
    primary_server           = Column(String(255))
    primary_database         = Column(String(128))
    secondary_server         = Column(String(255))
    secondary_database       = Column(String(128))
    last_backup_date         = Column(DateTime, nullable=True)
    last_backup_file         = Column(String(512), nullable=True)
    backup_threshold_minutes = Column(Integer, nullable=True)
    last_copy_date           = Column(DateTime, nullable=True)
    last_restore_date        = Column(DateTime, nullable=True)
    restore_threshold_minutes = Column(Integer, nullable=True)
    status                   = Column(Integer, nullable=True)   # 0=ok 1=warn 2=error
    out_of_sync              = Column(Boolean, default=False)


class AlertRule(Base):
    """User-defined alert thresholds."""
    __tablename__ = "alert_rules"

    id           = Column(Integer, primary_key=True, index=True)
    server_id    = Column(Integer, nullable=True)    # NULL = applies to all servers
    metric       = Column(String(80), nullable=False) # cpu_percent, blocked_sessions, etc.
    operator     = Column(String(5), default="gt")    # gt / lt / eq
    threshold    = Column(Float, nullable=False)
    severity     = Column(SAEnum(AlertSeverity), default=AlertSeverity.warning)
    enabled      = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)


class AlertEvent(Base):
    """Fired alert history."""
    __tablename__ = "alert_events"

    id           = Column(Integer, primary_key=True, index=True)
    server_id    = Column(Integer, nullable=False, index=True)
    rule_id      = Column(Integer, nullable=True)
    fired_at     = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at  = Column(DateTime, nullable=True)
    severity     = Column(SAEnum(AlertSeverity))
    metric       = Column(String(80))
    value        = Column(Float)
    threshold    = Column(Float)
    message      = Column(Text)
    acknowledged = Column(Boolean, default=False)


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_db():
    """FastAPI dependency – yields a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
