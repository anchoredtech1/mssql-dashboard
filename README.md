# MSSQL Dashboard

<div align="center">

![MSSQL Dashboard](https://img.shields.io/badge/MSSQL-Dashboard-1a6cf5?style=for-the-badge&logo=microsoftsqlserver&logoColor=white)
![Version](https://img.shields.io/badge/version-1.1.0-00e5a0?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-yellow?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Electron](https://img.shields.io/badge/Electron-30-47848F?style=for-the-badge&logo=electron&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)

**A free, self-hosted SQL Server monitoring dashboard.**  
No cloud. No subscription. No data leaving your network.

[⬇ Download Desktop App (.exe)](https://github.com/anchoredtech1/mssql-dashboard/releases/latest) &nbsp;·&nbsp; [📖 Docs](#installation) &nbsp;·&nbsp; [🐛 Report a Bug](https://github.com/anchoredtech1/mssql-dashboard/issues) &nbsp;·&nbsp; [💡 Request a Feature](https://github.com/anchoredtech1/mssql-dashboard/issues)

---

Built by **[Anchored Tech Solutions](https://anchoredtechsolutions.com)**

</div>

---

## What's New in v1.1.0

- 🖥️ **Native Desktop App** — double-click to launch, no browser required
- ⚡ **React Frontend** — live charts, real-time metrics, tabbed detail views
- 🔔 **System Tray** — minimize to tray, keep monitoring in the background
- 🔄 **Auto-Update** — new versions install automatically via GitHub Releases
- 📦 **Windows Installer** — Start Menu + Desktop shortcuts via NSIS

---

## What It Monitors

| Module | What You See |
|---|---|
| 💻 **Server Health** | CPU %, memory, active/blocked sessions, top wait stats |
| 🔄 **Availability Groups** | Replica roles, sync state, redo queue lag, failover mode |
| 🖥️ **FCI Clusters** | Active node, all cluster nodes, shared disk health |
| 📦 **Log Shipping** | Backup/copy/restore times, threshold violation alerts |
| 🔔 **Alert Rules** | Custom thresholds with severity levels and event history |
| 🗃️ **Metric History** | 7-day rolling snapshots stored locally for trend analysis |

---

## Supported Auth Types

| Auth Type | When to Use |
|---|---|
| **SQL Server Auth** | Standard username + password login |
| **Windows / Integrated Auth** | Domain accounts, no password stored in app |
| **TLS / Certificate Auth** | Encrypted connections, AWS RDS with custom CA certs |

All credentials are **encrypted at rest** using Fernet AES-256 symmetric encryption. Your passwords never touch the cloud.

---

## Requirements

### For the Desktop App (.exe installer)

| Requirement | Version | Download |
|---|---|---|
| Windows | 10 or 11 (64-bit) | — |
| Python | 3.11+ | [python.org](https://python.org) ✅ Add to PATH |
| ODBC Driver for SQL Server | 17 or 18 | [aka.ms/odbc18](https://aka.ms/odbc18) |

> **The installer will check for Python and ODBC Driver** and prompt you to install them if missing.

### SQL Server Permissions

Your monitoring login needs `VIEW SERVER STATE` at minimum:

```sql
-- Create dedicated monitoring login
CREATE LOGIN [mssql_monitor] WITH PASSWORD = 'YourStrongPassword!';

-- Required: CPU, memory, sessions, waits
GRANT VIEW SERVER STATE TO [mssql_monitor];

-- Required: database list and states
GRANT VIEW ANY DATABASE TO [mssql_monitor];

-- Required for log shipping monitoring
USE msdb;
GRANT SELECT ON dbo.log_shipping_monitor_primary   TO [mssql_monitor];
GRANT SELECT ON dbo.log_shipping_monitor_secondary TO [mssql_monitor];
GRANT SELECT ON dbo.log_shipping_monitor_history   TO [mssql_monitor];
```

---

## Installation

### Option 1 — Desktop App (Recommended)

1. Go to [Releases](https://github.com/anchoredtech1/mssql-dashboard/releases/latest)
2. Download **`MSSQL-Dashboard-Setup-1.1.0.exe`**
3. Run the installer — creates Start Menu + Desktop shortcuts
4. Launch **MSSQL Dashboard** from the desktop
5. The app starts the backend automatically and opens the dashboard window

> **Portable version available:** `MSSQL-Dashboard-1.1.0.exe` — no install needed, just run it.

### Option 2 — Manual / Server Install

For headless servers or advanced deployments:

**Windows:**
```powershell
# 1. Extract the release ZIP
# 2. Install Python dependencies
cd mssql-dashboard\installer
pip install -r requirements.txt

# 3. Start the backend
cd ..\backend
uvicorn main:app --host 127.0.0.1 --port 8080

# 4. Open in browser
start http://localhost:8080
```

**Linux / macOS:**
```bash
cd mssql-dashboard/installer
chmod +x install.sh && ./install.sh
# Then open: http://localhost:8080
```

---

## How It Works

```
User launches MSSQL Dashboard.exe
        ↓
Electron starts Python/FastAPI backend (localhost:8080)
        ↓
React frontend loads in the native app window
        ↓
Dashboard polls SQL Server instances via ODBC every 30-60s
        ↓
Metrics stored locally in SQLite (7-day rolling)
        ↓
Closing the window → minimizes to system tray
Backend keeps running — right-click tray to quit
```

**Data flow is entirely local.** Nothing leaves your network.

---

## Adding Your First Server

1. Click **+ Add Server** in the top-right
2. Enter the hostname, VNN listener, or IP address
3. Select your auth type (SQL, Windows, or TLS/Cert)
4. Set the **Role** (Standalone, AG Primary, AG Secondary, FCI, Log Ship)
5. Click **Test Connection** → **Save**

### FCI / AG Clusters
Connect using the **VNN** or **AG Listener name** — not individual node IPs. The ODBC driver handles failover automatically.

### AWS RDS / TLS Certificate Auth
1. Download your RDS CA bundle from the AWS console (`.pem`)
2. Place it anywhere accessible (e.g. `C:\certs\rds-ca.pem`)
3. Select **TLS/Certificate** auth and enter the full cert path

---

## Project Structure

```
mssql-dashboard/
├── backend/                        # Python FastAPI backend
│   ├── main.py                     # FastAPI entry point + CORS
│   ├── database.py                 # SQLite ORM models (SQLAlchemy)
│   ├── crypto.py                   # Fernet AES-256 credential encryption
│   ├── scheduler.py                # APScheduler background polling
│   ├── connections/
│   │   ├── builder.py              # Connection string builder (all 3 auth types)
│   │   └── manager.py              # Thread-safe ODBC connection pool
│   ├── queries/
│   │   ├── health.py               # CPU, memory, sessions, wait stats
│   │   ├── ag.py                   # Availability Group queries
│   │   ├── fci.py                  # FCI cluster node/disk queries
│   │   └── log_shipping.py         # Log shipping status queries
│   └── routers/
│       ├── servers.py              # Server registry CRUD + test connection
│       ├── metrics.py              # Live health + history endpoints
│       ├── clusters.py             # AG + FCI + log shipping endpoints
│       └── alerts.py               # Alert rules + event history
│
├── frontend/                       # React frontend (Vite)
│   ├── src/
│   │   ├── App.jsx                 # Main app: sidebar, server detail, tabs
│   │   └── main.jsx                # React entry point
│   ├── package.json
│   ├── vite.config.js              # Proxies /api → localhost:8080
│   └── index.html
│
├── electron/                       # Desktop app wrapper
│   ├── src/
│   │   ├── main.js                 # Main process: window, tray, backend spawn
│   │   ├── preload.js              # Secure IPC bridge (contextIsolation)
│   │   └── loading.html            # Startup screen while backend initializes
│   ├── assets/                     # App icons (.ico, .png, tray-icon.png)
│   ├── scripts/
│   │   └── installer.nsh           # NSIS installer customization
│   └── package.json                # electron-builder config
│
├── installer/                      # Manual install scripts
│   ├── requirements.txt
│   ├── install.bat                 # Windows one-click
│   └── install.sh                  # Linux/macOS
│
├── .github/
│   └── workflows/
│       ├── build.yml               # Builds .exe installer on version tags
│       └── ci.yml                  # Runs validation tests on push/PR
│
├── .gitignore                      # Excludes key.secret, *.db, __pycache__
└── README.md
```

---

## API Reference

Full interactive docs available at `http://localhost:8080/docs` (Swagger UI).

| Endpoint | Method | Description |
|---|---|---|
| `/api/servers` | GET | List all registered servers |
| `/api/servers` | POST | Register a new server |
| `/api/servers/{id}` | DELETE | Remove a server and all its data |
| `/api/servers/{id}/test` | POST | Test connection to a server |
| `/api/metrics/{id}/health` | GET | Live CPU, memory, session snapshot |
| `/api/metrics/{id}/history` | GET | Historical metrics (hours param) |
| `/api/metrics/{id}/sessions` | GET | Active and blocked session detail |
| `/api/metrics/{id}/waits` | GET | Top wait stats |
| `/api/clusters/{id}/ag/summary` | GET | AG replica roles and sync state |
| `/api/clusters/{id}/fci` | GET | FCI node status and shared drives |
| `/api/clusters/{id}/logshipping` | GET | Log shipping backup/restore status |
| `/api/alerts/rules` | GET/POST | Alert threshold rules |
| `/api/alerts/events` | GET | Recent alert events (hours param) |
| `/api/alerts/unacked-count` | GET | Count of unacknowledged alerts |

---

## Security

| Control | Detail |
|---|---|
| **Credential Encryption** | Fernet AES-256 — passwords encrypted before SQLite storage |
| **Encryption Key** | `key.secret` — local filesystem only, excluded from git |
| **Network Binding** | API binds to `127.0.0.1` only — not exposed to internet |
| **SQL Permissions** | Read-only (`VIEW SERVER STATE`) — no write access needed |
| **Electron Hardening** | `contextIsolation: true`, `nodeIntegration: false`, `webSecurity: true` |
| **No Telemetry** | Zero data transmitted externally — fully air-gapped capable |

> ⚠️ **Back up `key.secret`** — losing it means losing access to stored credentials.  
> For shared intranet access, consider putting nginx in front with basic authentication.

---

## Building from Source

### Prerequisites
- Node.js 20+ — [nodejs.org](https://nodejs.org)
- Python 3.11+ — [python.org](https://python.org)

### Build the Frontend
```powershell
cd frontend
npm install
npm run build        # outputs to frontend/dist/
```

### Run in Dev Mode (no Electron)
```powershell
# Terminal 1 — backend
cd backend
pip install -r ../installer/requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8080 --reload

# Terminal 2 — frontend dev server
cd frontend
npm run dev          # opens http://localhost:3000 with HMR
```

### Build Desktop App
```powershell
# Build frontend first (see above), then:
cd electron
npm install
npm run build        # creates electron/dist/*.exe
```

### Create a GitHub Release
```powershell
git tag v1.1.0
git push origin v1.1.0
# GitHub Actions builds the .exe and publishes the release automatically
```

---

## Roadmap

- [x] **v1.0.0** — Full backend API (FastAPI + Python)
- [x] **v1.1.0** — React frontend + Electron desktop app *(current)*
- [ ] **v1.2.0** — Email / Slack / Teams alert notifications
- [ ] **v1.3.0** — Query performance top offenders (long-running queries, missing indexes)
- [ ] **v1.4.0** — Multi-user support with nginx reverse proxy config guide

---

## Contributing

Pull requests welcome. For major changes, please open an issue first.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## Support

- **Bugs / features:** [Open an issue](https://github.com/anchoredtech1/mssql-dashboard/issues)
- **Professional DBA services:** [anchoredtechsolutions.com](https://anchoredtechsolutions.com)
- **Custom monitoring solutions:** [Contact us](https://anchoredtechsolutions.com/#contact)

---

## License

MIT License — free to use, modify, and distribute.

---

<div align="center">
Built with ❤️ by <a href="https://anchoredtechsolutions.com">Anchored Tech Solutions, LLC</a>
</div>
