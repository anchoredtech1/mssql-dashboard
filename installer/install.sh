#!/bin/bash
set -e

echo "============================================================"
echo "  MSSQL Dashboard - Linux/macOS Installer"
echo "============================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    echo "        Install via your package manager or https://python.org"
    exit 1
fi
echo "[OK] Python found: $(python3 --version)"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "[ERROR] pip3 not found. Install python3-pip."
    exit 1
fi

# Install dependencies
echo ""
echo "[INFO] Installing Python dependencies..."
pip3 install -r installer/requirements.txt --quiet
echo "[OK] Dependencies installed"

# Init DB
echo ""
echo "[INFO] Initializing database..."
cd backend
python3 -c "from database import init_db; init_db(); print('[OK] Database ready')"

# Start
echo ""
echo "============================================================"
echo "  Starting MSSQL Dashboard..."
echo "  Open your browser to: http://localhost:8080"
echo "  API Docs:             http://localhost:8080/docs"
echo "  Press Ctrl+C to stop."
echo "============================================================"
echo ""
uvicorn main:app --host 0.0.0.0 --port 8080
