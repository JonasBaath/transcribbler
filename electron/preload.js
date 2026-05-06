const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  pickFolder: () => ipcRenderer.invoke('pick-folder'),
  onMenuClick: (callback) => ipcRenderer.on('menu-click', (_event, btnId) => callback(btnId)),
  setMenuLang: (lang) => ipcRenderer.send('set-menu-lang', lang),
  titlebarDoubleClick: () => ipcRenderer.send('titlebar-double-click'),
  savePdf: (defaultName) => ipcRenderer.invoke('save-pdf', defaultName),
  platform: process.platform,
});
