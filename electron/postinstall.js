// Runs after `npm install` on macOS to rebrand the Electron app bundle.
// 1. Renames dist/Electron.app → dist/Transcribbler.app
// 2. Updates node_modules/electron/path.txt to match
// 3. Patches Info.plist (CFBundleName, CFBundleDisplayName, CFBundleIdentifier)
'use strict';
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

if (process.platform !== 'darwin') process.exit(0);

const electronPkg = path.join('node_modules', 'electron');
const dist = path.join(electronPkg, 'dist');
const from = path.join(dist, 'Electron.app');
const to   = path.join(dist, 'Transcribbler.app');
const pathTxt = path.join(electronPkg, 'path.txt');

// Rename bundle (idempotent)
if (fs.existsSync(from)) {
  if (fs.existsSync(to)) fs.rmSync(to, { recursive: true });
  fs.renameSync(from, to);
  console.log('postinstall: renamed Electron.app → Transcribbler.app');
}

// Update path.txt
if (fs.existsSync(pathTxt)) {
  const txt = fs.readFileSync(pathTxt, 'utf8');
  fs.writeFileSync(pathTxt, txt.replace('Electron.app', 'Transcribbler.app'));
  console.log('postinstall: updated path.txt');
}

// Patch Info.plist
const plist = path.join(to, 'Contents', 'Info.plist');
if (fs.existsSync(plist)) {
  execSync(`plutil -replace CFBundleName        -string Transcribbler           "${plist}"`);
  execSync(`plutil -replace CFBundleDisplayName -string Transcribbler           "${plist}"`);
  execSync(`plutil -replace CFBundleIdentifier  -string se.jonasbaaath.transcribbler "${plist}"`);
  console.log('postinstall: patched Info.plist');
}
