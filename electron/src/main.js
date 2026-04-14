'use strict';

const { app, BrowserWindow, Tray, Menu, shell, ipcMain, dialog, Notification } = require('electron');
const { autoUpdater } = require('electron-updater');
const log = require('electron-log');
const Store = require('electron-store');
const path = require('path');
const { spawn, exec } = require('child_process');
const fs = require('fs');
const net = require('net');

// ── LOGGING ───────────────────────────────────────────────────────────────────
log.transports.file.level = 'info';
log.transports.console.level = 'debug';
autoUpdater.logger = log;

// ── STORE (persistent settings) ───────────────────────────────────────────────
const store = new Store({
  defaults: {
    windowBounds: { width: 1400, height: 900 },
    startMinimized: false,
    launchOnStartup: false,
    apiPort: 8080,
    theme: 'dark',
  }
});

// ── GLOBALS ───────────────────────────────────────────────────────────────────
let mainWindow = null;
let tray = null;
let pythonProcess = null;
let backendReady = false;
let isQuitting = false;
const API_PORT = store.get('apiPort', 8080);
const isPackaged = app.isPackaged;

// ── PATHS ─────────────────────────────────────────────────────────────────────
// Step up two levels since main.js is inside electron/src
const basePath = isPackaged 
  ? process.resourcesPath 
  : path.join(__dirname, '..', '..');

const backendPath = path.join(basePath, 'backend');
const frontendPath = path.join(basePath, 'frontend');

// Find Python executable
function findPython() {
  if (process.platform === 'win32') {
    return 'C:\\Users\\lksan\\AppData\\Local\\Programs\\Python\\Python314\\python.exe';
  }

  const candidates = [
    path.join(backendPath, 'venv', 'Scripts', 'python.exe'),
    path.join(backendPath, 'venv', 'bin', 'python'),
    'python',
    'python3',
    'py'
  ];

  for (const c of candidates) {
    if (c.includes(path.sep) && !fs.existsSync(c)) continue;
    return c;
  }
  return 'python';
}

// ── PORT CHECK ────────────────────────────────────────────────────────────────
function isPortFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(false));
    server.once('listening', () => { server.close(); resolve(true); });
    server.listen(port, '127.0.0.1');
  });
}

function waitForPort(port, retries = 120, delay = 500) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const check = () => {
      const client = net.createConnection({ port, host: '127.0.0.1' });
      client.once('connect', () => { client.destroy(); resolve(); });
      client.once('error', () => {
        client.destroy();
        if (++attempts >= retries) reject(new Error(`Backend did not start on port ${port}`));
        else setTimeout(check, delay);
      });
    };
    check();
  });
}

// ── START PYTHON BACKEND ──────────────────────────────────────────────────────
async function startBackend() {
   // Kill any leftover backend process from a previous run
  if (process.platform === 'win32') {
    exec('taskkill /f /im mssql_backend.exe', () => {}); // ignore errors if not running
    await new Promise(r => setTimeout(r, 500)); // give it a moment to die
  }

    const portFree = await isPortFree(API_PORT);
  if (!portFree) {
    log.info(`Port ${API_PORT} already in use — assuming backend is running`);
    backendReady = true;
    return;
  }

  const dbPath = path.join(app.getPath('userData'), 'mssql_dashboard.db');
  const keyPath = path.join(app.getPath('userData'), 'key.secret');

  const env = {
    ...process.env,
    DB_PATH: dbPath,
    KEY_FILE: keyPath,
    API_PORT: String(API_PORT),
    PYTHONUNBUFFERED: '1',
  };

  let command, args;

  // 1. Check for the compiled standalone executable first (Production)
  const compiledExe = process.platform === 'win32' 
    ? path.join(backendPath, 'dist', 'mssql_backend', 'mssql_backend.exe')
    : path.join(backendPath, 'dist', 'mssql_backend', 'mssql_backend');

  if (fs.existsSync(compiledExe)) {
    log.info(`Found standalone backend: ${compiledExe}`);
    command = compiledExe;
    args = []; // Arguments are handled inside run_backend.py
  } 
  // 2. Fallback to raw Python script (Development)
  else {
    log.info('Standalone backend not found, falling back to Python script...');
    command = findPython();
    args = ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(API_PORT), '--log-level', 'warning'];
    env.PYTHONPATH = backendPath;
  }

  log.info(`Starting backend: ${command} ${args.join(' ')}`);
  log.info(`DB path: ${dbPath}`);

  pythonProcess = spawn(command, args, {
    cwd: backendPath,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  });

  pythonProcess.stdout?.on('data', (d) => log.info(`[backend] ${d.toString().trim()}`));
  pythonProcess.stderr?.on('data', (d) => log.warn(`[backend] ${d.toString().trim()}`));

  pythonProcess.on('exit', (code) => {
    log.warn(`Backend exited with code ${code}`);
    backendReady = false;
    if (!isQuitting && mainWindow) {
      mainWindow.webContents.send('backend-died', code);
    }
  });

  pythonProcess.on('error', (err) => {
    log.error(`Failed to start backend: ${err.message}`);
    dialog.showErrorBox('Backend Start Failed', `Could not start the backend.\n\nError: ${err.message}`);
  });

  try {
    await waitForPort(API_PORT);
    backendReady = true;
    log.info(`Backend ready on port ${API_PORT}`);
  } catch (err) {
    log.error(`Backend never became ready: ${err.message}`);
    throw err;
  }
}

// ── STOP BACKEND ─────────────────────────────────────────────────────────────
function stopBackend() {
  if (!pythonProcess) return;
  log.info('Stopping backend...');
  try {
    if (process.platform === 'win32') {
      exec(`taskkill /pid ${pythonProcess.pid} /T /F`, (err) => {
        if (err) log.warn('taskkill error:', err.message);
      });
    } else {
      pythonProcess.kill('SIGTERM');
    }
  } catch (e) {
    log.warn('Error stopping backend:', e.message);
  }
  pythonProcess = null;
}

// ── CREATE WINDOW ─────────────────────────────────────────────────────────────
function createWindow() {
  const { width, height } = store.get('windowBounds');

  mainWindow = new BrowserWindow({
    width,
    height,
    minWidth: 900,
    minHeight: 600,
    frame: false,          // custom title bar
    titleBarStyle: 'hidden',
    backgroundColor: '#0a0f1e',
    icon: path.join(__dirname, '..', 'assets', 'icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true,
    },
    show: false,
  });

  // Show a loading screen while backend starts
  mainWindow.loadFile(path.join(__dirname, 'loading.html'));
  mainWindow.once('ready-to-show', () => {
    if (!store.get('startMinimized')) mainWindow.show();
  });

  // Load the React Frontend via the backend (avoids file:// ES module issues)
  const tryLoad = async () => {
    try {
      if (backendReady) {
        log.info(`Loading frontend from backend at http://localhost:${API_PORT}`);
        mainWindow.loadURL(`http://localhost:${API_PORT}`);
      } else {
        setTimeout(tryLoad, 300);
      }
    } catch (e) {
      log.error('Load error:', e);
    }
  };
  setTimeout(tryLoad, 200);

  // Save window size on resize
  mainWindow.on('resize', () => {
    const [w, h] = mainWindow.getSize();
    store.set('windowBounds', { width: w, height: h });
  });

  // Minimize to tray instead of closing
  mainWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow.hide();
      if (Notification.isSupported()) {
        new Notification({
          title: 'MSSQL Dashboard',
          body: 'Still monitoring in the background. Right-click the tray icon to quit.',
          icon: path.join(__dirname, '..', 'assets', 'icon.png'),
        }).show();
      }
    }
  });

  mainWindow.on('closed', () => { mainWindow = null; });

  // Open external links in browser, not in Electron
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

// ── SYSTEM TRAY ───────────────────────────────────────────────────────────────
function createTray() {
  const iconPath = path.join(__dirname, '..', 'assets', 'tray-icon.png');
  try {
    tray = new Tray(fs.existsSync(iconPath) ? iconPath : path.join(__dirname, '..', 'assets', 'icon.ico'));
  } catch (e) {
    log.warn('Tray icon missing, skipping tray initialization.');
    return; // Exits the function safely without crashing
  }

  const updateMenu = () => {
    const menu = Menu.buildFromTemplate([
      {
        label: 'MSSQL Dashboard',
        enabled: false,
        icon: fs.existsSync(iconPath) ? iconPath : undefined,
      },
      { type: 'separator' },
      {
        label: mainWindow?.isVisible() ? 'Hide Window' : 'Show Window',
        click: () => {
          if (mainWindow?.isVisible()) mainWindow.hide();
          else { mainWindow?.show(); mainWindow?.focus(); }
          updateMenu();
        }
      },
      { type: 'separator' },
      {
        label: `Backend: ${backendReady ? '🟢 Running' : '🔴 Stopped'}`,
        enabled: false
      },
      {
        label: `Port: ${API_PORT}`,
        enabled: false
      },
      { type: 'separator' },
      {
        label: 'Open in Browser',
        click: () => shell.openExternal(`http://localhost:${API_PORT}`)
      },
      {
        label: 'API Docs (Swagger)',
        click: () => shell.openExternal(`http://localhost:${API_PORT}/docs`)
      },
      { type: 'separator' },
      {
        label: 'Check for Updates',
        click: () => autoUpdater.checkForUpdatesAndNotify()
      },
      {
        label: 'Settings',
        click: () => {
          mainWindow?.show();
          mainWindow?.webContents.send('open-settings');
        }
      },
      { type: 'separator' },
      {
        label: 'Quit MSSQL Dashboard',
        click: () => {
          isQuitting = true;
          app.quit();
        }
      }
    ]);
    tray.setContextMenu(menu);
  };

  tray.setToolTip('MSSQL Dashboard');
  updateMenu();

  tray.on('double-click', () => {
    if (mainWindow?.isVisible()) mainWindow.focus();
    else mainWindow?.show();
    updateMenu();
  });

  // Update tray menu every 10s to reflect backend status
  setInterval(updateMenu, 10000);
}

// ── IPC HANDLERS ──────────────────────────────────────────────────────────────
function setupIPC() {
  // Window controls (custom title bar)
  ipcMain.on('window-minimize', () => mainWindow?.minimize());
  ipcMain.on('window-maximize', () => {
    if (mainWindow?.isMaximized()) mainWindow.unmaximize();
    else mainWindow?.maximize();
  });
  ipcMain.on('window-close', () => mainWindow?.close());
  ipcMain.on('window-hide', () => mainWindow?.hide());

  // App info
  ipcMain.handle('get-app-version', () => app.getVersion());
  ipcMain.handle('get-backend-status', () => ({ ready: backendReady, port: API_PORT }));
  ipcMain.handle('get-data-path', () => app.getPath('userData'));

  // Settings
  ipcMain.handle('get-setting', (_, key) => store.get(key));
  ipcMain.handle('set-setting', (_, key, value) => {
    store.set(key, value);
    if (key === 'launchOnStartup') {
      app.setLoginItemSettings({ openAtLogin: value, name: 'MSSQL Dashboard' });
    }
  });

  // Open external
  ipcMain.on('open-external', (_, url) => shell.openExternal(url));

  // Show notification
  ipcMain.on('show-notification', (_, { title, body }) => {
    if (Notification.isSupported()) {
      new Notification({ title, body }).show();
    }
  });

  // Restart backend
  ipcMain.handle('restart-backend', async () => {
    stopBackend();
    backendReady = false;
    await startBackend();
    return { success: backendReady };
  });
}

// ── AUTO UPDATER ──────────────────────────────────────────────────────────────
function setupAutoUpdater() {
  autoUpdater.on('update-available', (info) => {
    log.info('Update available:', info.version);
    mainWindow?.webContents.send('update-available', info);
  });

  autoUpdater.on('update-downloaded', (info) => {
    log.info('Update downloaded:', info.version);
    const response = dialog.showMessageBoxSync(mainWindow, {
      type: 'info',
      buttons: ['Restart Now', 'Later'],
      title: 'Update Ready',
      message: `MSSQL Dashboard ${info.version} is ready to install.`,
      detail: 'Restart now to apply the update.',
    });
    if (response === 0) {
      isQuitting = true;
      autoUpdater.quitAndInstall();
    }
  });

  autoUpdater.on('error', (err) => log.error('AutoUpdater error:', err));

  // Check for updates 30s after start, then every 4h
  setTimeout(() => autoUpdater.checkForUpdatesAndNotify(), 30000);
  setInterval(() => autoUpdater.checkForUpdatesAndNotify(), 4 * 60 * 60 * 1000);
}

// ── APP LIFECYCLE ─────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  log.info(`MSSQL Dashboard ${app.getVersion()} starting...`);
  log.info(`Platform: ${process.platform} ${process.arch}`);
  log.info(`Backend Path: ${backendPath}`);
  log.info(`User data: ${app.getPath('userData')}`);

  setupIPC();

  try {
    await startBackend();
  } catch (err) {
    log.error('Backend failed to start:', err.message);
    // Still create window — user can debug from there
  }

  createWindow();
  createTray();

  if (isPackaged) setupAutoUpdater();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
    else mainWindow?.show();
  });
});

app.on('before-quit', () => { isQuitting = true; });

app.on('will-quit', () => {
  log.info('App quitting — stopping backend');
  stopBackend();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    // Don't quit — keep running in tray
  }
});

// Handle second instance (single instance lock)
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}