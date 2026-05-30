const { app, BrowserWindow, ipcMain } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const fs   = require('fs')

let mainWindow   = null
let agentProcess = null

function startAgent() {
  const venvPython  = path.join(__dirname, '..', 'venv', 'Scripts', 'python.exe')
  const agentScript = path.join(__dirname, '..', 'agent', 'main.py')
  const pythonBin   = fs.existsSync(venvPython) ? venvPython : 'python'

  console.log('[main] Agent başlatılıyor:', pythonBin)
  agentProcess = spawn(pythonBin, [agentScript], {
    cwd: path.join(__dirname, '..'),
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', ELECTRON_RUN_AS_NODE: undefined }
  })

  agentProcess.stdout.on('data', d => process.stdout.write('[agent] ' + d.toString()))
  agentProcess.stderr.on('data', d => process.stderr.write('[agent-err] ' + d.toString()))
  agentProcess.on('exit', code => console.log('[agent] Çıktı, kod:', code))
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    title: 'AI Video Editor',
    backgroundColor: '#0d0d0d',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))

  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools()
  }

  mainWindow.on('closed', () => { mainWindow = null })
}

app.whenReady().then(() => {
  startAgent()
  setTimeout(createWindow, 2000)
})

app.on('window-all-closed', () => {
  if (agentProcess) agentProcess.kill()
  if (process.platform !== 'darwin') app.quit()
})

ipcMain.handle('get-app-path', () => app.getPath('userData'))
