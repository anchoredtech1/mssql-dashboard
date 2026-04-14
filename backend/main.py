"""
main.py – FastAPI application entry point
Run with:  uvicorn main:app --host 0.0.0.0 --port 8080 --reload
Swagger:   http://localhost:8080/docs
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db
from scheduler import start_scheduler, stop_scheduler
from routers import servers, metrics, clusters, alerts

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MSSQL Dashboard API...")
    init_db()
    logger.info("SQLite database initialized")
    start_scheduler()
    yield
    logger.info("Shutting down...")
    stop_scheduler()
    from connections.manager import pool
    pool.close_all()


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MSSQL Dashboard API",
    description=(
        "Local/intranet MSSQL monitoring dashboard.\n\n"
        "Supports SQL Auth, Windows Auth, and TLS/Certificate auth.\n"
        "Monitors standalone, FCI, AG, and log-shipping topologies."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS – allow localhost frontend dev server ────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(servers.router,  prefix="/api")
app.include_router(metrics.router,  prefix="/api")
app.include_router(clusters.router, prefix="/api")
app.include_router(alerts.router,   prefix="/api")


# ── Static frontend (served from /frontend/dist after build) ─────────────────
_STATIC_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
)
logger.info(f"Static dir resolved to: {_STATIC_DIR} (exists={os.path.isdir(_STATIC_DIR)})")
if os.path.isdir(_STATIC_DIR):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
    logger.info(f"Serving frontend from {_STATIC_DIR}")
else:
    logger.warning(f"Frontend dist not found at {_STATIC_DIR} — skipping static mount")


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/api/ping", tags=["system"])
def ping():
    return {"status": "ok", "service": "MSSQL Dashboard API"}


@app.get("/api/version", tags=["system"])
def version():
    return {
        "version": "1.0.0",
        "python":  __import__("sys").version,
    }
