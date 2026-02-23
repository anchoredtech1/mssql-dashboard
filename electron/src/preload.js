'use strict';

const { contextBridge, ipcRenderer } = require('electron');

// Expose a safe, limited API to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // Window controls
  minimize:  () => ipcRenderer.send('window-minimize'),
  maximize:  () => ipcRenderer.send('window-maximize'),
  close:     () => ipcRenderer.send('window-close'),
  hide:      () => ipcRenderer.send('window-hide'),

  // App info
  getVersion:       () => ipcRenderer.invoke('get-app-version'),
  getBackendStatus: () => ipcRenderer.invoke('get-backend-status'),
  getDataPath:      () => ipcRenderer.invoke('get-data-path'),

  // Settings
  getSetting: (key)        => ipcRenderer.invoke('get-setting', key),
  setSetting: (key, value) => ipcRenderer.invoke('set-setting', key, value),

  // Actions
  openExternal:      (url)           => ipcRenderer.send('open-external', url),
  showNotification:  (title, body)   => ipcRenderer.send('show-notification', { title, body }),
  restartBackend:    ()              => ipcRenderer.invoke('restart-backend'),

  // Event listeners (renderer listens for main process events)
  onBackendDied:     (cb) => ipcRenderer.on('backend-died',     (_, code) => cb(code)),
  onUpdateAvailable: (cb) => ipcRenderer.on('update-available', (_, info) => cb(info)),
  onOpenSettings:    (cb) => ipcRenderer.on('open-settings',    ()        => cb()),

  // Remove listeners
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
});
