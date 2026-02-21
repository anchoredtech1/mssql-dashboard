@echo off
SETLOCAL

echo ============================================================
echo   MSSQL Dashboard - Windows Installer
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Download Python 3.11+ from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found

:: Check ODBC Driver
reg query "HKLM\SOFTWARE\ODBC\ODBCINST.INI\ODBC Driver 18 for SQL Server" >nul 2>&1
IF ERRORLEVEL 1 (
    reg query "HKLM\SOFTWARE\ODBC\ODBCINST.INI\ODBC Driver 17 for SQL Server" >nul 2>&1
    IF ERRORLEVEL 1 (
        echo.
        echo [WARNING] Microsoft ODBC Driver 17 or 18 for SQL Server not found.
        echo           Download from: https://aka.ms/odbc18
        echo           The dashboard requires this driver to connect to SQL Server.
        echo.
    ) ELSE (
        echo [OK] ODBC Driver 17 found
    )
) ELSE (
    echo [OK] ODBC Driver 18 found
)

:: Install Python dependencies
echo.
echo [INFO] Installing Python dependencies...
pip install -r installer\requirements.txt --quiet
IF ERRORLEVEL 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed

:: Initialize DB + encryption key
echo.
echo [INFO] Initializing database...
cd backend
python -c "from database import init_db; init_db(); print('[OK] Database ready')"
IF ERRORLEVEL 1 (
    echo [ERROR] Database init failed.
    pause
    exit /b 1
)

:: Start the server
echo.
echo ============================================================
echo   Starting MSSQL Dashboard...
echo   Open your browser to: http://localhost:8080
echo   API Docs:             http://localhost:8080/docs
echo   Press Ctrl+C to stop.
echo ============================================================
echo.
start "" "http://localhost:8080"
uvicorn main:app --host 0.0.0.0 --port 8080

ENDLOCAL
