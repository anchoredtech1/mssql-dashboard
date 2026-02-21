@echo off
SETLOCAL

echo ============================================================
echo   MSSQL Dashboard - Frontend Build
echo ============================================================
echo.

:: Check Node.js
node --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Node.js is not installed.
    echo         Download from: https://nodejs.org  (LTS version)
    pause
    exit /b 1
)
echo [OK] Node.js found: 
node --version

:: Install dependencies
echo.
echo [INFO] Installing frontend dependencies...
cd frontend
call npm install
IF ERRORLEVEL 1 (
    echo [ERROR] npm install failed.
    pause
    exit /b 1
)
echo [OK] Dependencies installed

:: Build
echo.
echo [INFO] Building frontend...
call npm run build
IF ERRORLEVEL 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)
echo [OK] Frontend built to frontend/dist/

echo.
echo ============================================================
echo   Frontend build complete!
echo   Now run install.bat to start the full dashboard.
echo ============================================================
pause
ENDLOCAL
