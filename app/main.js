// main.js - Nixie Clock Companion (Electron). Wraps the offline build-guide site and allows the
// Tools page to talk to the clock's Arduino Nano over USB serial (Web Serial API).
// Security: no Node.js in pages, context isolation and sandbox on, navigation locked to the bundled
// files, every web link opens in the system browser.
const { app, BrowserWindow, shell, session } = require('electron');
const path = require('path');
const { pathToFileURL } = require('url');

const WWW = path.join(__dirname, 'www');
const WWW_URL = pathToFileURL(WWW + path.sep).href;
// USB vendor IDs commonly found on Arduino Nano boards and clones: Arduino, WCH CH340, FTDI, Silicon Labs CP210x.
// Electron reports vendorId as a string; accept either hex or decimal spelling.
const PREFERRED_VENDORS = ['2341', '1a86', '0403', '10c4'].flatMap((h) => [h, String(parseInt(h, 16))]);

function isLocal(url) {
  return url.startsWith(WWW_URL);
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 380,
    backgroundColor: '#120e0b',
    title: 'Nixie Clock Companion',
    icon: path.join(__dirname, 'www', 'img', 'icon-512.png'),
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  win.removeMenu();
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/i.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  win.webContents.on('will-navigate', (event, url) => {
    if (isLocal(url)) return;
    event.preventDefault();
    if (/^https?:/i.test(url)) shell.openExternal(url);
  });
  win.loadFile(path.join(WWW, 'index.html'));
}

app.whenReady().then(() => {
  const ses = session.defaultSession;
  // Allow Web Serial only for the bundled pages.
  ses.setPermissionCheckHandler((wc, permission, origin) => permission === 'serial' && (origin === 'file://' || origin === '' || isLocal(origin)));
  ses.setDevicePermissionHandler((details) => details.deviceType === 'serial');
  // Electron has no built-in port chooser: pick the most likely Nano, else the first port.
  ses.on('select-serial-port', (event, portList, webContents, callback) => {
    event.preventDefault();
    const id = (p) => String(p.vendorId || '').toLowerCase().replace(/^0x/, '');
    const nano = portList.find((p) => PREFERRED_VENDORS.includes(id(p)) || PREFERRED_VENDORS.includes(id(p).padStart(4, '0')));
    const chosen = nano || portList[0];
    callback(chosen ? chosen.portId : '');
  });
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
