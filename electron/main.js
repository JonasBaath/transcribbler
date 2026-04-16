const { app, BrowserWindow, shell, dialog, ipcMain, Menu } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');
const http = require('http');
const fs = require('fs');

// Set app name (shown in macOS menu bar and dock)
app.setName('Transcribbler');

// Each window gets its own Flask backend; track them as { window, flask, port }.
const instances = [];

// Try a stable port first so localStorage (origin-bound) survives between runs.
// Falls back to a random free port if the preferred port is occupied.
const PREFERRED_PORT = 53917;

// Reserve a port atomically: hold the socket open until the caller releases it,
// so no other process can grab the same port in between.
function reservePort(preferred) {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.once('error', () => {
      // preferred port busy — grab any free port instead
      const srv2 = net.createServer();
      srv2.once('error', reject);
      srv2.listen(0, '127.0.0.1', () => {
        const p = srv2.address().port;
        resolve({ port: p, release: () => new Promise(r => srv2.close(r)) });
      });
    });
    srv.listen(preferred, '127.0.0.1', () => {
      const p = srv.address().port;
      resolve({ port: p, release: () => new Promise(r => srv.close(r)) });
    });
  });
}

function getAppDir() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'app')
    : path.join(__dirname, '..');
}

function findPython(appDir) {
  const bundled = app.isPackaged
    ? (process.platform === 'win32'
        ? path.join(process.resourcesPath, 'python-runtime', 'python.exe')
        : path.join(process.resourcesPath, 'python-runtime', 'bin', 'python3'))
    : null;

  const candidates = [
    ...(bundled ? [bundled] : []),
    ...(process.platform === 'win32'
      ? [path.join(appDir, 'venv', 'Scripts', 'python.exe'), 'python']
      : [path.join(appDir, 'venv', 'bin', 'python3'), 'python3', 'python']),
  ];

  for (const c of candidates) {
    if (!c.includes(path.sep) || fs.existsSync(c)) return c;
  }
  return 'python3';
}

function startFlask(port) {
  const appDir = getAppDir();
  const py = findPython(appDir);

  const proc = spawn(py, [path.join(appDir, 'main.py'), '--no-browser'], {
    cwd: appDir,
    env: { ...process.env, PORT: String(port) },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  proc.stdout.on('data', d => process.stdout.write(`[flask:${port}] ` + d));
  proc.stderr.on('data', d => process.stderr.write(`[flask:${port}] ` + d));
  return proc;
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
    const focused = BrowserWindow.getFocusedWindow();
    if (focused) {
      focused.webContents.send('menu-click', id);
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

  const win = new BrowserWindow({
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

  win.loadURL(`http://127.0.0.1:${port}`);

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  return win;
}

// IPC: Double-click titlebar to maximize/restore (macOS hiddenInset workaround)
ipcMain.on('titlebar-double-click', (event) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (!win) return;
  if (win.isMaximized()) {
    win.unmaximize();
  } else {
    win.maximize();
  }
});

// IPC: Electron-native folder picker
ipcMain.handle('pick-folder', async (event) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  const result = await dialog.showOpenDialog(win, {
    properties: ['openDirectory'],
    title: 'Välj projektmapp',
  });
  return result.canceled ? '' : result.filePaths[0];
});

function killFlaskProcess(proc) {
  if (!proc) return;
  const pid = proc.pid;
  if (process.platform === 'win32') {
    require('child_process').spawn('taskkill', ['/F', '/T', '/PID', String(pid)], { stdio: 'ignore' });
  } else {
    try { process.kill(pid, 'SIGTERM'); } catch (_) {}
  }
}

function killAllFlask() {
  for (const inst of instances) {
    killFlaskProcess(inst.flask);
    inst.flask = null;
  }
}

// Spin up a new Flask backend + window and track the pair.
async function launchInstance() {
  const preferred = instances.length === 0 ? PREFERRED_PORT : 0;
  const { port, release } = await reservePort(preferred);
  // Release the held socket so Flask can bind to the same port immediately.
  await release();
  const flask = startFlask(port);

  try {
    await waitForFlask(port);
  } catch {
    dialog.showErrorBox(
      'Transcribbler',
      'Kunde inte starta Flask-servern.\nKontrollera att Python och beroenden är installerade.'
    );
    killFlaskProcess(flask);
    if (instances.length === 0) app.quit();
    return;
  }

  const win = createWindow(port);
  const inst = { window: win, flask, port };
  instances.push(inst);

  win.on('closed', () => {
    killFlaskProcess(inst.flask);
    inst.flask = null;
    const idx = instances.indexOf(inst);
    if (idx !== -1) instances.splice(idx, 1);
    // Quit when the last window is closed (on all platforms).
    if (instances.length === 0) app.quit();
  });
}

// Allow a second launch of the same app to open a new parallel window.
// requestSingleInstanceLock makes the OS route the second launch to this
// process (via the 'second-instance' event) instead of starting a new one.
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  // Another instance is already primary — it will handle the event. Quit this one.
  app.quit();
} else {
  app.on('second-instance', () => {
    // A second launch was attempted — open a new independent window + backend.
    launchInstance();
  });
}

app.whenReady().then(async () => {
  if (process.platform === 'darwin') {
    const iconPath = path.join(__dirname, 'assets', 'icon.png');
    if (fs.existsSync(iconPath)) {
      try { app.dock.setIcon(iconPath); } catch (e) { console.warn('dock.setIcon failed:', e.message); }
    }
  }

  buildMenu();
  await launchInstance();

  app.on('activate', () => {
    // macOS: re-open a window when dock icon is clicked and no windows exist.
    if (instances.length === 0) launchInstance();
  });
});

app.on('before-quit', killAllFlask);
