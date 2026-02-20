# GitHub Setup Guide — MSSQL Dashboard

Step-by-step instructions to publish the project on GitHub so people can download it from your website.

---

## Step 1: Create the GitHub Repository

1. Go to **https://github.com** and sign in to your account (or create one)
2. Click the **+** icon (top-right) → **New repository**
3. Fill in:
   - **Repository name:** `mssql-dashboard`
   - **Description:** `Free self-hosted SQL Server monitoring dashboard — no cloud required`
   - **Visibility:** ✅ Public (so anyone can download without an account)
   - **Initialize:** Leave ALL checkboxes unchecked (we're pushing existing code)
4. Click **Create repository**

GitHub will show you a page with push instructions — keep it open.

---

## Step 2: Push the Code to GitHub

Open a terminal/command prompt, navigate to the project folder, and run:

```bash
cd path\to\mssql-dashboard

# Initialize git (first time only)
git init
git branch -M main

# Connect to your GitHub repo (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/mssql-dashboard.git

# Stage all files
git add .

# First commit
git commit -m "Initial release: backend foundation v1.0.0"

# Push to GitHub
git push -u origin main
```

> **Note:** If GitHub asks for credentials, use your GitHub username and a **Personal Access Token** (not your password). Create one at: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → New token → check `repo` scope.

---

## Step 3: Create Your First Release (v1.0.0)

This is what generates the downloadable ZIP file on GitHub.

### Option A — Using the GitHub Website (Easiest)

1. Go to your repo page: `https://github.com/YOUR_USERNAME/mssql-dashboard`
2. Click **Releases** (right sidebar) → **Create a new release**
3. Click **Choose a tag** → type `v1.0.0` → click **+ Create new tag: v1.0.0**
4. **Release title:** `MSSQL Dashboard v1.0.0`
5. In the description box, paste this:

```
## What's in this release
- Full backend API (FastAPI + Python)
- SQL Auth, Windows Auth, and TLS/Certificate Auth support
- AG, FCI, and Log Shipping monitoring queries
- SQLite local storage with Fernet encrypted credentials
- Background polling scheduler with configurable intervals
- Alert rules and event history
- One-click install.bat for Windows

## Requirements
- Python 3.11+ → https://python.org
- ODBC Driver 17 or 18 → https://aka.ms/odbc18

See the README for full installation instructions.
```

6. Scroll down to **Assets** → Click **Attach binaries** → Upload your ZIP file
   - Or let the GitHub Actions workflow (already included) build it automatically when you push the tag
7. Click **Publish release**

### Option B — Using a Git Tag (Triggers Automatic ZIP Build)

Once you've pushed the code, just push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The GitHub Actions workflow in `.github/workflows/release.yml` will automatically:
- Build the clean ZIP (no `.git`, no secrets, no `*.db` files)
- Create the GitHub Release
- Attach the ZIP as a downloadable asset

Check the progress at: `https://github.com/YOUR_USERNAME/mssql-dashboard/actions`

---

## Step 4: Get Your Download Link

After the release is published, your permanent download link will be:

```
https://github.com/YOUR_USERNAME/mssql-dashboard/releases/latest/download/mssql-dashboard-v1.0.0.zip
```

The `/releases/latest/download/` path always points to the **most recent** release, so when you publish v1.1.0 later, the link on your website automatically serves the new version without any changes.

---

## Step 5: Update Your Website Download Page

In the `mssql-dashboard-page.html` file, find these two buttons and update the links:

```html
<!-- Change this: -->
<a href="/downloads/mssql-dashboard-v1.0.0.zip" ...>

<!-- To this: -->
<a href="https://github.com/YOUR_USERNAME/mssql-dashboard/releases/latest/download/mssql-dashboard-v1.0.0.zip" ...>


<!-- And this GitHub link: -->
<a href="https://github.com/anchoredtechsolutions/mssql-dashboard" ...>

<!-- To this (same URL, just make sure the username is right): -->
<a href="https://github.com/YOUR_USERNAME/mssql-dashboard" ...>
```

---

## Step 6: Releasing Future Versions

Every time you add new features (like the v1.1.0 React frontend), releasing is just two commands:

```bash
# Stage and commit your changes
git add .
git commit -m "v1.1.0: Add React frontend dashboard"

# Push the code
git push origin main

# Tag the new version — this triggers the auto-release workflow
git tag v1.1.0
git push origin v1.1.0
```

GitHub Actions builds the ZIP and publishes the release automatically. Your website download link stays the same.

---

## Repository Settings to Configure

Once the repo is created, set these up:

### Topics (for discoverability)
Go to repo page → gear icon next to About → add topics:
```
sql-server  mssql  database-monitoring  dba  fastapi  python  free  self-hosted
```

### About Section
- **Website:** `https://anchoredtechsolutions.com/mssql-dashboard`
- **Description:** `Free self-hosted SQL Server monitoring dashboard`
- Check ✅ **Releases**
- Check ✅ **Packages**

### Branch Protection (Optional but recommended)
Go to Settings → Branches → Add rule → Branch name: `main` → Check "Require pull request reviews before merging"

---

## File Structure That Will Be on GitHub

```
mssql-dashboard/
├── .github/
│   └── workflows/
│       ├── release.yml     ← Auto-builds ZIP on version tags
│       └── ci.yml          ← Runs tests on every push
├── backend/
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
├── installer/
│   ├── requirements.txt
│   ├── install.bat
│   └── install.sh
├── .gitignore              ← Keeps secrets/DB files out of GitHub
├── README.md               ← What people see on the GitHub page
└── GITHUB_SETUP.md         ← This file
```

---

## What the .gitignore Protects

These files are **automatically excluded** from GitHub — they will never be committed:

| File | Why Excluded |
|---|---|
| `key.secret` | Encryption key — never share this |
| `*.pem`, `*.cer` | TLS certificates |
| `*.db`, `*.sqlite` | Local databases with your server list |
| `.env` | Environment variables |
| `certs/` | Certificate folder |
| `__pycache__/` | Python compiled files |

---

## Quick Reference

| Action | Command |
|---|---|
| First push | `git add . && git commit -m "Initial" && git push -u origin main` |
| Push changes | `git add . && git commit -m "message" && git push` |
| Create release | `git tag v1.0.0 && git push origin v1.0.0` |
| Check actions | `https://github.com/YOUR_USERNAME/mssql-dashboard/actions` |
| View releases | `https://github.com/YOUR_USERNAME/mssql-dashboard/releases` |
