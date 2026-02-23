# Desktop App Setup Guide

How to add the Electron desktop wrapper to your project and build the Windows installer.

---

## Folder Structure After Adding Electron

```
mssql-dashboard/          ← your existing GitHub repo
├── backend/              ← Python FastAPI (existing)
├── frontend/             ← React app (new from Phase 2)
│   ├── src/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── electron/             ← NEW: Desktop app wrapper
│   ├── src/
│   │   ├── main.js       ← Electron main process
│   │   ├── preload.js    ← Secure IPC bridge
│   │   └── loading.html  ← Startup screen
│   ├── assets/           ← App icons (you add these)
│   │   ├── icon.ico
│   │   ├── icon.png
│   │   └── tray-icon.png
│   ├── scripts/
│   │   └── installer.nsh ← NSIS installer customization
│   ├── package.json
│   └── .github/
│       └── workflows/
│           └── build.yml ← Auto-builds .exe on GitHub
├── installer/            ← Existing manual install scripts
├── .gitignore
└── README.md
```

---

## Step 1 — Add the Files to Your Project

Copy the `electron/` folder into your `C:\Users\lksan\Downloads\dashboard\` folder.

Your dashboard folder should now have: `backend/`, `frontend/`, `electron/`, `installer/`, `README.md`

---

## Step 2 — Add App Icons

The app needs icon files. Create/add these to `electron/assets/`:

| File | Size | Used For |
|---|---|---|
| `icon.ico` | 256x256 | Windows app icon, taskbar, installer |
| `icon.png` | 512x512 | Linux, notifications |
| `tray-icon.png` | 16x16 or 32x32 | System tray (small!) |

**Quick option:** Use any free icon generator:
- https://www.favicon.io/favicon-converter/ — upload a PNG, download `.ico`
- Use your ATS logo from the website

**Minimum to get started:** Just an `icon.ico` file. The build won't fail without the tray icon, it'll just use the main icon.

---

## Step 3 — Install Node.js (if not already installed)

Download **Node.js LTS** from https://nodejs.org

Verify:
```powershell
node --version
npm --version
```

---

## Step 4 — Build the Frontend First

```powershell
cd C:\Users\lksan\Downloads\dashboard\frontend
npm install
npm run build
```

This creates `frontend/dist/` which Electron bundles into the app.

---

## Step 5 — Test the Desktop App Locally

```powershell
cd C:\Users\lksan\Downloads\dashboard\electron
npm install
npm start
```

This opens the desktop app window. The app will:
1. Show the loading screen
2. Start the Python backend automatically
3. Load the dashboard in the window

If Python isn't found, you'll see an error dialog with instructions.

---

## Step 6 — Build the Windows Installer

```powershell
cd C:\Users\lksan\Downloads\dashboard\electron
npm run build
```

This creates two files in `electron/dist/`:
- `MSSQL-Dashboard-Setup-1.1.0.exe` — Full installer with Start Menu + Desktop shortcuts
- `MSSQL-Dashboard-1.1.0.exe` — Portable version, no install needed

---

## Step 7 — Push to GitHub and Create Release

```powershell
cd C:\Users\lksan\Downloads\dashboard
git add .
git commit -m "Add Electron desktop app and React frontend"
git push origin main

git tag v1.1.0
git push origin v1.1.0
```

GitHub Actions will automatically:
1. Build the React frontend
2. Build the Windows `.exe` installer
3. Create the GitHub Release with the installer attached

Watch it at: https://github.com/anchoredtech1/mssql-dashboard/actions

---

## How the App Works

```
User double-clicks MSSQL Dashboard.exe
        ↓
Electron checks if Python is available
        ↓
Starts: uvicorn main:app --host 127.0.0.1 --port 8080
        ↓
Shows loading screen while backend starts (~3-5 seconds)
        ↓
Loads http://127.0.0.1:8080 in the app window
        ↓
Full dashboard is live — no browser needed!
        ↓
User closes window → minimizes to system tray
        ↓
Backend keeps running in background
        ↓
Right-click tray icon → Quit to fully stop
```

---

## System Tray Features

Right-click the tray icon (bottom-right of screen) to:
- Show/hide the window
- See backend status (green/red)
- Open in browser instead
- Open Swagger API docs
- Check for updates
- Quit the app completely

---

## Data Storage

User data is stored in:
- **Windows:** `C:\Users\{username}\AppData\Roaming\mssql-dashboard\`
  - `mssql_dashboard.db` — your server list, snapshots, alerts
  - `key.secret` — encryption key (back this up!)

This means uninstalling and reinstalling keeps your server configuration intact.

---

## Troubleshooting

**"Python not found" error on startup:**
Install Python 3.11+ from https://python.org and make sure "Add to PATH" is checked during install.

**"ODBC Driver not found" when testing connections:**
Install ODBC Driver 18 from https://aka.ms/odbc18

**App opens but shows blank screen:**
The backend failed to start. Check:
```powershell
cd C:\Users\lksan\Downloads\dashboard\backend
python -m uvicorn main:app --port 8080
```
Look for error messages.

**Port 8080 already in use:**
Change the port in `electron/src/main.js` line: `const API_PORT = store.get('apiPort', 8080);`
Change `8080` to `8181` (or any free port).
