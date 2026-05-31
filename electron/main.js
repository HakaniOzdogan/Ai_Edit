const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const fs   = require('fs')

let mainWindow   = null
let agentProcess = null

// ── Agent Yolu: Paketlenmiş vs Geliştirme ─────────────────────────────────────
function getAgentCommand() {
  if (app.isPackaged) {
    // Paketlenmiş .exe — extraResources içinden al
    const agentExe = path.join(process.resourcesPath, 'agent.exe')
    if (fs.existsSync(agentExe)) {
      return { bin: agentExe, args: [], cwd: process.resourcesPath }
    }
    dialog.showErrorBox('Agent Bulunamadı',
      `agent.exe bulunamadı: ${agentExe}\nUygulamayı yeniden kurun.`)
    app.quit()
  }

  // Geliştirme modu — venv Python
  const venvPython  = path.join(__dirname, '..', 'venv', 'Scripts', 'python.exe')
  const agentScript = path.join(__dirname, '..', 'agent', 'main.py')
  const pythonBin   = fs.existsSync(venvPython) ? venvPython : 'python'
  return { bin: pythonBin, args: [agentScript], cwd: path.join(__dirname, '..') }
}

function startAgent() {
  const { bin, args, cwd } = getAgentCommand()
  console.log('[main] Agent başlatılıyor:', bin)

  agentProcess = spawn(bin, args, {
    cwd,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {
      ...process.env,
      PYTHONIOENCODING:    'utf-8',
      ELECTRON_RUN_AS_NODE: '',      // packaged ortamda da temizle
    }
  })

  agentProcess.stdout.on('data', d => process.stdout.write('[agent] ' + d.toString()))
  agentProcess.stderr.on('data', d => process.stderr.write('[agent-err] ' + d.toString()))
  agentProcess.on('exit', (code, signal) => {
    console.log(`[agent] Çıkış — kod: ${code}, sinyal: ${signal}`)
    if (code !== 0 && code !== null && mainWindow) {
      mainWindow.webContents.send('agent-crashed', { code })
    }
  })
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width:    1400,
    height:   900,
    minWidth: 1200,
    minHeight: 700,
    title:    'AI Video Editor',
    backgroundColor: '#0d0d0d',
    webPreferences: {
      preload:          path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration:  false,
    }
  })

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))

  // Renderer console mesajlarini ana process'e yonlendir
  mainWindow.webContents.on('console-message', (e, level, msg, line, src) => {
    const lvl = ['V','I','W','E'][level] || '?'
    console.log(`[renderer:${lvl}] ${msg}`)
  })

  if (!app.isPackaged) {
    mainWindow.webContents.openDevTools()
  }

  mainWindow.on('closed', () => { mainWindow = null })
}

async function waitForAgent(maxMs = 40000) {
  const start = Date.now()
  let attempt = 0
  while (Date.now() - start < maxMs) {
    attempt++
    try {
      const res = await fetch('http://localhost:8765/health', { signal: AbortSignal.timeout(1500) })
      if (res.ok) {
        console.log(`[main] Agent hazır (${attempt}. denemede, ${Math.round((Date.now()-start)/1000)}sn)`)
        return true
      }
    } catch {}
    await new Promise(r => setTimeout(r, 500))
  }
  console.warn(`[main] Agent ${maxMs/1000}sn içinde yanıt vermedi`)
  return false
}

// ── Uygulama Yaşam Döngüsü ────────────────────────────────────────────────────
app.whenReady().then(async () => {
  // Agent zaten calisiyor mu? (start.ps1 onceden baslattiysa tekrar baslat ma)
  const alreadyRunning = await waitForAgent(2000)
  if (alreadyRunning) {
    console.log('[main] Agent zaten calisiyor, yeniden baslatilmiyor')
  } else {
    startAgent()
    console.log('[main] Agent bekleniyor (max 40sn)...')
    const ready = await waitForAgent(40000)
    if (!ready) console.warn('[main] Agent baslamadi, pencere yine de aciliyor')
  }
  createWindow()
})

app.on('window-all-closed', () => {
  if (agentProcess) {
    agentProcess.kill()
    agentProcess = null
  }
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  if (agentProcess) agentProcess.kill()
})

// ── IPC Handlers ──────────────────────────────────────────────────────────────
ipcMain.handle('get-app-path',    () => app.getPath('userData'))
ipcMain.handle('get-version',     () => app.getVersion())
ipcMain.handle('is-packaged',     () => app.isPackaged)
ipcMain.handle('open-file-dialog', async (_, opts) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: opts?.multiple ? ['openFile', 'multiSelections'] : ['openFile'],
    filters:    opts?.filters || []
  })
  return result.filePaths
})
