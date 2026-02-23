# GitHub Setup Guide — MSSQL Dashboard

Step-by-step reference for managing the repository, building releases, and deploying updates.

> **Already set up?** Jump to [Releasing a New Version](#releasing-a-new-version).

---

## Repository

| | |
|---|---|
| **URL** | https://github.com/anchoredtech1/mssql-dashboard |
| **Visibility** | Public |
| **Current version** | v1.1.0 |
| **License** | MIT |

---

## How Releases Work

Pushing a version tag triggers two GitHub Actions workflows automatically:

```
git tag v1.1.0 && git push origin v1.1.0
         ↓
┌─────────────────────────────────────────────────────────┐
│  build.yml                                              │
│  1. Build React frontend  (ubuntu-latest)               │
│  2. Build Windows .exe installer  (windows-latest)      │
│  3. Create GitHub Release with .exe attached            │
└─────────────────────────────────────────────────────────┘
         ↓
Release page:
https://github.com/anchoredtech1/mssql-dashboard/releases

Download links (always point to latest):
  .exe installer  → /releases/latest/download/MSSQL-Dashboard-Setup-*.exe
  Portable .exe   → /releases/latest/download/MSSQL-Dashboard-*.exe
```

---

## Releasing a New Version

This is the day-to-day workflow once everything is set up.

### 1 — Stage and Commit Changes

```powershell
cd C:\Users\lksan\Downloads\dashboard

git add .
git commit -m "Description of what changed"
git push origin main
```

### 2 — Build the Frontend

Before tagging, make sure the React frontend is built:

```powershell
cd frontend
npm install
npm run build        # outputs to frontend/dist/
cd ..
```

### 3 — Tag the Release

```powershell
# Replace X.X.X with the new version number
git tag vX.X.X
git push origin vX.X.X
```

### 4 — Watch the Build

Go to **https://github.com/anchoredtech1/mssql-dashboard/actions**

You'll see two workflow runs:
- **CI** — validates Python imports and tests (~20s)
- **Build Desktop App** — builds the .exe installer (~5-8 min)

Both should show ✅ green. If either fails, click on it to see the error log.

### 5 — Verify the Release

Go to **https://github.com/anchoredtech1/mssql-dashboard/releases**

You should see the new version with two `.exe` files attached:
- `MSSQL-Dashboard-Setup-X.X.X.exe` — full installer
- `MSSQL-Dashboard-X.X.X.exe` — portable version

---

## Version History

| Version | What Changed |
|---|---|
| **v1.1.0** | Electron desktop app, React frontend, system tray, auto-update |
| **v1.0.0** | Initial release — FastAPI backend, SQLite storage, encrypted credentials |

---

## Full Folder Structure on GitHub

```
mssql-dashboard/
├── .github/
│   └── workflows/
│       ├── build.yml           ← Builds .exe installer on version tags
│       └── ci.yml              ← Validates Python + runs tests on push/PR
│
├── backend/                    ← Python FastAPI backend
│   ├── main.py
│   ├── database.py
│   ├── crypto.py
│   ├── scheduler.py
│   ├── connections/
│   │   ├── builder.py
│   │   └── manager.py
│   ├── queries/
│   │   ├── health.py
│   │   ├── ag.py
│   │   ├── fci.py
│   │   └── log_shipping.py
│   └── routers/
│       ├── servers.py
│       ├── metrics.py
│       ├── clusters.py
│       └── alerts.py
│
├── frontend/                   ← React frontend (Vite)
│   ├── src/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
│
├── electron/                   ← Desktop app wrapper (Electron)
│   ├── src/
│   │   ├── main.js             ← Main process: window, tray, Python spawn
│   │   ├── preload.js          ← Secure IPC bridge
│   │   └── loading.html        ← Startup screen
│   ├── assets/                 ← icon.ico, icon.png, tray-icon.png
│   ├── scripts/
│   │   └── installer.nsh       ← NSIS installer customization
│   └── package.json            ← electron-builder config
│
├── installer/                  ← Manual install scripts
│   ├── requirements.txt
│   ├── install.bat
│   └── install.sh
│
├── .gitignore
├── README.md
├── GITHUB_SETUP.md             ← This file
└── DESKTOP_APP_SETUP.md        ← Electron build instructions
```

---

## What the .gitignore Protects

These files are **never committed to GitHub**:

| File / Pattern | Why Excluded |
|---|---|
| `key.secret` | Fernet encryption key — never share this |
| `*.db`, `*.sqlite` | Local SQLite database with your server configs |
| `*.pem`, `*.cer` | TLS certificates |
| `certs/` | Certificate folder |
| `.env` | Environment variables |
| `__pycache__/` | Python bytecode |
| `node_modules/` | npm packages (restored via `npm install`) |
| `frontend/dist/` | Built frontend (rebuilt by GitHub Actions) |
| `electron/dist/` | Built installers (produced by GitHub Actions) |

---

## Personal Access Token

GitHub requires a token (not your password) for command-line pushes.

**Create / Renew a token:**
1. Go to https://github.com/settings/tokens
2. Click **Tokens (classic)** → **Generate new token (classic)**
3. Set expiration (90 days recommended)
4. Check these scopes: ✅ `repo` &nbsp; ✅ `workflow`
5. Click **Generate token** — copy it immediately

**Use when prompted during `git push`:**
- Username: `anchoredtech1`
- Password: *(paste the token)*

**Store the token so you don't get prompted every time:**
```powershell
git config --global credential.helper manager
```
Windows Credential Manager will save it after the first use.

---

## GitHub Actions — Workflow Details

### `build.yml` — Desktop App Builder
Triggers on: version tags matching `v*.*.*`

| Step | Runs On | What It Does |
|---|---|---|
| Build frontend | ubuntu-latest | `npm ci && npm run build` in `frontend/` |
| Build Windows installer | windows-latest | `npm ci && npm run build` in `electron/` |
| Create release | ubuntu-latest | Creates GitHub Release, attaches `.exe` files |

### `ci.yml` — Continuous Integration
Triggers on: every push to `main`/`develop` and all pull requests

| Step | What It Tests |
|---|---|
| Python imports | `database`, `crypto`, `connections.builder` all import cleanly |
| Encryption | Fernet encrypt/decrypt round-trip works |
| Connection builder | All 3 auth types (SQL, Windows, TLS) build valid strings |
| FastAPI startup | App loads without errors |

---

## Repository Settings

### Topics (for GitHub discoverability)
Repo page → gear icon next to **About** → add:
```
sql-server  mssql  database-monitoring  dba  fastapi  python  electron  self-hosted  free
```

### About Section
- **Website:** `https://anchoredtechsolutions.com/mssql-dashboard`
- **Description:** `Free self-hosted SQL Server monitoring dashboard — desktop app included`
- Check ✅ **Releases**

### Branch Protection (Recommended)
Settings → Branches → Add rule → Branch: `main`
- ✅ Require status checks to pass before merging
- Select: **CI** workflow as required check

---

## Quick Reference

| Task | Command |
|---|---|
| Push changes | `git add . && git commit -m "message" && git push` |
| Create release | `git tag v1.1.0 && git push origin v1.1.0` |
| Delete a tag (redo) | `git tag -d v1.1.0 && git push origin --delete v1.1.0` |
| Check build status | https://github.com/anchoredtech1/mssql-dashboard/actions |
| View releases | https://github.com/anchoredtech1/mssql-dashboard/releases |
| Latest .exe link | `/releases/latest/download/MSSQL-Dashboard-Setup-*.exe` |
| Swagger API docs | http://localhost:8080/docs *(when backend is running)* |
