# MSSQL Dashboard

## 🚀 How to Run the Dashboard

This project uses a FastAPI backend and a React (Vite) frontend. You will need both running to view the dashboard.

### 1. Build the Frontend
First, install the Node dependencies and compile the React code:
\`\`\`bash
cd frontend
npm install
npm run build
\`\`\`
*Requires [Node.js](https://nodejs.org).*

### 2. Start the Backend
Open a new terminal, navigate to the backend folder, install the Python requirements, and start the server:
\`\`\`bash
cd backend
python -m pip install -r ../installer/requirements.txt
python -m uvicorn main:app --port 8080
\`\`\`
*Requires Python 3.8+.*

### 3. View the Dashboard
Once the server says "Application startup complete", open your web browser and navigate to:
**http://localhost:8080**
<div align="center">

![MSSQL Dashboard](https://img.shields.io/badge/MSSQL-Dashboard-1a6cf5?style=for-the-badge&logo=microsoftsqlserver&logoColor=white)
![Version](https://img.shields.io/badge/version-1.0.0-00e5a0?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-yellow?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)

**A free, self-hosted SQL Server monitoring dashboard.**  
No cloud. No subscription. No data leaving your network.

[⬇ Download Latest Release](https://github.com/anchoredtechsolutions/mssql-dashboard/releases/latest) &nbsp;·&nbsp; [📖 Docs](#installation) &nbsp;·&nbsp; [🐛 Report a Bug](https://github.com/anchoredtechsolutions/mssql-dashboard/issues) &nbsp;·&nbsp; [💡 Request a Feature](https://github.com/anchoredtechsolutions/mssql-dashboard/issues)

---

Built by the DBAs at **[Anchored Tech Solutions](https://anchoredtechsolutions.com)**

</div>

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
| **Windows / Integrated Auth** | Domain accounts, no password stored |
| **TLS / Certificate Auth** | Encrypted connections, AWS RDS with custom CA certs |

All credentials are **encrypted at rest** using Fernet symmetric encryption. Your passwords never touch the cloud.

---

## Requirements

Before installing, make sure you have:

| Requirement | Version | Download |
|---|---|---|
| Python | 3.11+ | [python.org](https://python.org) |
| ODBC Driver for SQL Server | 17 or 18 | [aka.ms/odbc18](https://aka.ms/odbc18) |
| Visual C++ Redistributable | 2019+ (Windows only) | [Download](https://aka.ms/vs/17/release/vc_redist.x64.exe) |

Your SQL Server login needs `VIEW SERVER STATE` permission at minimum:
```sql
GRANT VIEW SERVER STATE TO [your_monitoring_login];
```

For log shipping monitoring, also grant read access to `msdb`:
```sql
USE msdb;
GRANT SELECT ON dbo.log_shipping_monitor_primary   TO [your_monitoring_login];
GRANT SELECT ON dbo.log_shipping_monitor_secondary TO [your_monitoring_login];
```

---

## Installation

### Windows (Recommended)

1. [Download the latest release ZIP](https://github.com/anchoredtechsolutions/mssql-dashboard/releases/latest)
2. Extract to any folder (e.g. `C:\mssql-dashboard`)
3. Double-click **`install.bat`**
4. Your browser will open automatically to `http://localhost:8080`

### Linux / macOS

```bash
curl -L https://github.com/anchoredtechsolutions/mssql-dashboard/releases/latest/download/mssql-dashboard.zip -o mssql-dashboard.zip
unzip mssql-dashboard.zip
cd mssql-dashboard
chmod +x installer/install.sh
./installer/install.sh
```

Then open: **http://localhost:8080**

### Manual Install (Any Platform)

```bash
pip install -r installer/requirements.txt
cd backend
python -c "from database import init_db; init_db()"
uvicorn main:app --host 0.0.0.0 --port 8080
```

---

## Adding Your First Server

1. Open `http://localhost:8080`
2. Click **Add Server**
3. Enter the hostname, VNN listener name, or IP address
4. Select your auth type (SQL, Windows, or TLS/Cert)
5. Click **Test Connection** then **Save**

### For TLS / Certificate Servers (AWS RDS, etc.)

1. Download your CA certificate (`.pem` or `.cer`) from the AWS RDS console
2. Place it in a `certs/` folder inside the dashboard directory
3. Select **TLS/Certificate** auth type when adding the server
4. Enter the full path to the cert file

### For FCI / AG Clusters

Connect using the **VNN (Virtual Network Name)** or **AG listener name** — not individual node hostnames. The ODBC driver handles failover routing automatically.

---

## Project Structure

```
mssql-dashboard/
├── backend/
│   ├── main.py                    # FastAPI entry point → /docs for Swagger UI
│   ├── database.py                # SQLite ORM models
│   ├── crypto.py                  # Fernet credential encryption
│   ├── scheduler.py               # Background metric polling
│   ├── connections/
│   │   ├── builder.py             # Connection string builder (all 3 auth types)
│   │   └── manager.py             # Thread-safe connection pool
│   ├── queries/
│   │   ├── health.py              # CPU, memory, sessions, wait stats
│   │   ├── ag.py                  # Availability Group queries
│   │   ├── fci.py                 # FCI cluster queries
│   │   └── log_shipping.py        # Log shipping queries
│   └── routers/
│       ├── servers.py             # Server registry CRUD
│       ├── metrics.py             # Live health endpoints
│       ├── clusters.py            # AG + FCI + log shipping
│       └── alerts.py              # Alert rules + events
├── installer/
│   ├── requirements.txt
│   ├── install.bat                # Windows one-click setup
│   └── install.sh                 # Linux/macOS setup
└── README.md
```

---

## API Reference

Full interactive docs at `http://localhost:8080/docs` after starting.

| Endpoint | Description |
|---|---|
| `GET /api/servers` | List all registered servers |
| `POST /api/servers` | Register a new server |
| `POST /api/servers/{id}/test` | Test a connection |
| `GET /api/metrics/{id}/health` | Live health snapshot |
| `GET /api/metrics/{id}/sessions` | Active & blocked sessions |
| `GET /api/metrics/{id}/waits` | Top wait stats |
| `GET /api/clusters/{id}/ag` | AG replica detail |
| `GET /api/clusters/{id}/fci` | FCI node & disk status |
| `GET /api/clusters/{id}/logshipping` | Log shipping summary |
| `GET /api/alerts/rules` | Alert rules |
| `GET /api/alerts/events` | Recent alert events |

---

## Roadmap

- [x] **v1.0.0** — Full backend API (current)
- [ ] **v1.1.0** — React frontend: live charts, AG topology view, alert center
- [ ] **v1.2.0** — Email / Slack alert notifications
- [ ] **v1.3.0** — Single `.exe` installer via PyInstaller

---

## Security Notes

- Credentials encrypted at rest with **Fernet symmetric encryption** in local SQLite
- `key.secret` holds the encryption key — back it up and protect it
- **Do not expose port 8080 to the internet** — designed for local/intranet only
- For shared intranet use, consider putting nginx in front with basic auth

---

## Contributing

Pull requests welcome. For major changes, open an issue first.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit: `git commit -m 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## Support

- **Bugs / features:** [Open an issue](https://github.com/anchoredtechsolutions/mssql-dashboard/issues)
- **Professional DBA services:** [anchoredtechsolutions.com](https://anchoredtechsolutions.com)
- **Custom monitoring:** [Contact us](https://anchoredtechsolutions.com/#contact)

---

## License

MIT License — free to use, modify, and distribute.

---

<div align="center">
Built with ❤️ by <a href="https://anchoredtechsolutions.com">Anchored Tech Solutions, LLC</a>
</div>
