const { app, BrowserWindow, shell, dialog, ipcMain, Menu } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');
const http = require('http');
const fs = require('fs');

// Set app name (shown in macOS menu bar and dock)
app.setName('Transcribbler');

let flaskProcess = null;
let mainWindow = null;
let flaskPort = null;

function findFreePort() {
  return new Promise(resolve => {
    const srv = net.createServer();
    srv.listen(0, '127.0.0.1', () => {
      const p = srv.address().port;
      srv.close(() => resolve(p));
    });
  });
}

function getAppDir() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'app')
    : path.join(__dirname, '..');
}

function findPython(appDir) {
  const candidates = process.platform === 'win32'
    ? [path.join(appDir, 'venv', 'Scripts', 'python.exe'), 'python']
    : [path.join(appDir, 'venv', 'bin', 'python3'), 'python3', 'python'];

  for (const c of candidates) {
    if (!c.includes(path.sep) || fs.existsSync(c)) return c;
  }
  return 'python3';
}

function startFlask(port) {
  const appDir = getAppDir();
  const py = findPython(appDir);

  flaskProcess = spawn(py, [path.join(appDir, 'main.py'), '--no-browser'], {
    cwd: appDir,
    env: { ...process.env, PORT: String(port) },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  flaskProcess.stdout.on('data', d => process.stdout.write('[flask] ' + d));
  flaskProcess.stderr.on('data', d => process.stderr.write('[flask] ' + d));
}

function waitForFlask(port, timeout = 60000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    function check() {
      http.get(`http://127.0.0.1:${port}/`, () => resolve())
        .on('error', () => {
          if (Date.now() - start > timeout) {
            reject(new Error('timeout'));
          } else {
            setTimeout(check, 500);
          }
        });
    }
    setTimeout(check, 500);
  });
}

const menuLabels = {
  sv: {
    about: 'Om transcribbler', hide: 'Göm transcribbler', hideOthers: 'Göm övriga',
    showAll: 'Visa alla', quit: 'Avsluta transcribbler',
    file: 'Arkiv', close: 'Stäng fönster', quit: 'Avsluta',
    edit: 'Redigera', undo: 'Ångra', redo: 'Gör om', cut: 'Klipp ut',
    copy: 'Kopiera', paste: 'Klistra in', selectAll: 'Markera allt',
    tools: 'Verktyg', stats: 'Statistik', irr: 'IRR', codebook: 'Kodbok',
    codetree: 'Kodträd', matrix: 'Kodmatris', overlap: 'Kodöverlapp',
    merge: 'Slå ihop filer',
    view: 'Visa', reload: 'Ladda om', forceReload: 'Tvinga omladdning',
    devTools: 'Utvecklarverktyg', fullscreen: 'Helskärm',
    window: 'Fönster', minimize: 'Minimera', zoom: 'Zooma', front: 'Flytta till främsta',
    help: 'Hjälp', github: 'Transcribbler på GitHub',
  },
  en: {
    about: 'About transcribbler', hide: 'Hide transcribbler', hideOthers: 'Hide Others',
    showAll: 'Show All', quit: 'Quit transcribbler',
    file: 'File', close: 'Close Window', quit: 'Quit',
    edit: 'Edit', undo: 'Undo', redo: 'Redo', cut: 'Cut',
    copy: 'Copy', paste: 'Paste', selectAll: 'Select All',
    tools: 'Tools', stats: 'Statistics', irr: 'IRR', codebook: 'Codebook',
    codetree: 'Code tree', matrix: 'Code matrix', overlap: 'Code overlap',
    merge: 'Merge files',
    view: 'View', reload: 'Reload', forceReload: 'Force Reload',
    devTools: 'Developer Tools', fullscreen: 'Full Screen',
    window: 'Window', minimize: 'Minimize', zoom: 'Zoom', front: 'Bring All to Front',
    help: 'Help', github: 'Transcribbler on GitHub',
  },
};

function buildMenu(lang = 'sv') {
  const isMac = process.platform === 'darwin';
  const L = menuLabels[lang] || menuLabels.sv;

  function clickButton(id) {
    if (mainWindow) {
      mainWindow.webContents.send('menu-click', id);
    }
  }

  const template = [];

  if (isMac) {
    template.push({
      label: 'Transcribbler',
      submenu: [
        { label: L.about, role: 'about' },
        { type: 'separator' },
        { label: L.hide, role: 'hide' },
        { label: L.hideOthers, role: 'hideOthers' },
        { label: L.showAll, role: 'unhide' },
        { type: 'separator' },
        { label: L.quit, role: 'quit' },
      ],
    });
  }

  template.push({
    label: L.file,
    submenu: isMac
      ? [{ label: L.close, role: 'close', accelerator: 'CmdOrCtrl+W' }]
      : [{ label: L.quit,  role: 'quit',  accelerator: 'Alt+F4' }],
  });

  template.push({
    label: L.edit,
    submenu: [
      { label: L.undo, role: 'undo', accelerator: 'CmdOrCtrl+Z' },
      { label: L.redo, role: 'redo', accelerator: 'Shift+CmdOrCtrl+Z' },
      { type: 'separator' },
      { label: L.cut, role: 'cut', accelerator: 'CmdOrCtrl+X' },
      { label: L.copy, role: 'copy', accelerator: 'CmdOrCtrl+C' },
      { label: L.paste, role: 'paste', accelerator: 'CmdOrCtrl+V' },
      { label: L.selectAll, role: 'selectAll', accelerator: 'CmdOrCtrl+A' },
    ],
  });

  template.push({
    label: L.tools,
    submenu: [
      { label: L.stats,    click: () => clickButton('btn-stats') },
      { label: L.irr,      click: () => clickButton('btn-irr') },
      { label: L.codebook, click: () => clickButton('btn-codebook') },
      { label: L.codetree, click: () => clickButton('btn-codetree') },
      { label: L.matrix,   click: () => clickButton('btn-code-matrix') },
      { label: L.overlap,  click: () => clickButton('btn-cooccurrence') },
      { type: 'separator' },
      { label: L.merge,    click: () => clickButton('btn-merge') },
    ],
  });

  template.push({
    label: L.view,
    submenu: [
      { label: L.reload, role: 'reload', accelerator: 'CmdOrCtrl+R' },
      { label: L.forceReload, role: 'forceReload', accelerator: 'Shift+CmdOrCtrl+R' },
      { label: L.devTools, role: 'toggleDevTools', accelerator: isMac ? 'Alt+Cmd+I' : 'Ctrl+Shift+I' },
      { type: 'separator' },
      { label: L.fullscreen, role: 'togglefullscreen' },
    ],
  });

  if (isMac) {
    template.push({
      label: L.window,
      submenu: [
        { label: L.minimize, role: 'minimize' },
        { label: L.zoom, role: 'zoom' },
        { type: 'separator' },
        { label: L.front, role: 'front' },
      ],
    });
  }

  template.push({
    label: L.help,
    submenu: [
      { label: L.github, click: () => shell.openExternal('https://github.com/jonasbaath/transcribbler') },
    ],
  });

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

ipcMain.on('set-menu-lang', (_event, lang) => {
  buildMenu(lang);
});

function createWindow(port) {
  const isMac = process.platform === 'darwin';

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    title: 'Transcribbler',
    icon: path.join(__dirname, 'assets', 'icon.png'),
    titleBarStyle: isMac ? 'hiddenInset' : 'default',
    backgroundColor: '#1e1e2e',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadURL(`http://127.0.0.1:${port}`);

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC: Electron-native folder picker
ipcMain.handle('pick-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Välj projektmapp',
  });
  return result.canceled ? '' : result.filePaths[0];
});

function killFlask() {
  if (!flaskProcess) return;
  const pid = flaskProcess.pid;
  flaskProcess = null;
  if (process.platform === 'win32') {
    // Kill entire process tree on Windows (Python may spawn child workers)
    require('child_process').spawn('taskkill', ['/F', '/T', '/PID', String(pid)], { stdio: 'ignore' });
  } else {
    try { process.kill(pid, 'SIGTERM'); } catch (_) {}
  }
}

app.whenReady().then(async () => {
  if (process.platform === 'darwin') {
    app.dock.setIcon(path.join(__dirname, 'assets', 'icon.png'));
  }
  flaskPort = await findFreePort();
  startFlask(flaskPort);

  try {
    await waitForFlask(flaskPort);
  } catch {
    dialog.showErrorBox(
      'Transcribbler',
      'Kunde inte starta Flask-servern.\nKontrollera att Python och beroenden är installerade.'
    );
    app.quit();
    return;
  }

  buildMenu();
  createWindow(flaskPort);

  app.on('activate', () => {
    if (!mainWindow) createWindow(flaskPort);
  });
});

app.on('window-all-closed', () => {
  killFlask();
  app.quit();
});

app.on('before-quit', killFlask);
