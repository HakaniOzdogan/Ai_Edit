# PHASE 5 — Electron Masaüstü Uygulaması

Önceki adım: PHASE_4_CLAUDE.md (Claude API çalışıyor, tool döngüsü test edildi)
Sonraki adım: PHASE_6_UI.md

---

## Amaç

Electron ile Windows masaüstü uygulamasını oluştur.
Agent'ı otomatik başlat, WebSocket bağlantısını kur, temel pencereyi aç.

---

## 5.1 — Main Process

`electron/main.js`:

```javascript
const { app, BrowserWindow, ipcMain } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const fs   = require('fs')

let mainWindow = null
let agentProcess = null
const AGENT_WS_URL = 'ws://localhost:8765/ws'

function startAgent() {
  const venvPython = path.join(__dirname, '..', 'venv', 'Scripts', 'python.exe')
  const agentScript = path.join(__dirname, '..', 'agent', 'main.py')
  const pythonBin = fs.existsSync(venvPython) ? venvPython : 'python'

  console.log('[main] Agent başlatılıyor:', pythonBin)
  agentProcess = spawn(pythonBin, [agentScript], {
    cwd: path.join(__dirname, '..'),
    stdio: ['ignore', 'pipe', 'pipe']
  })

  agentProcess.stdout.on('data', d => console.log('[agent]', d.toString().trim()))
  agentProcess.stderr.on('data', d => console.error('[agent-err]', d.toString().trim()))
  agentProcess.on('exit', code => console.log('[agent] Çıktı, kod:', code))
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    title: 'AI Video Editor',
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
  // Agent'ın hazır olması için bekle
  setTimeout(createWindow, 2000)
})

app.on('window-all-closed', () => {
  if (agentProcess) agentProcess.kill()
  if (process.platform !== 'darwin') app.quit()
})

// IPC — Renderer'dan gelen dosya yolu isteği
ipcMain.handle('get-app-path', () => app.getPath('userData'))
```

---

## 5.2 — Preload (Güvenli Köprü)

`electron/preload.js`:

```javascript
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getAppPath:  ()    => ipcRenderer.invoke('get-app-path'),
  agentWsUrl:  ()    => 'ws://localhost:8765/ws',
  agentHttpUrl: ()   => 'http://localhost:8765',
  platform:    ()    => process.platform,
})
```

---

## 5.3 — Temel HTML İskeleti

`electron/renderer/index.html`:

```html
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Video Editor</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div id="app">
    <div id="titlebar">
      <span id="app-title">AI Video Editor</span>
      <span id="connection-status" class="status-dot disconnected" title="Agent bağlantısı"></span>
    </div>
    <div id="main-layout">
      <div id="left-panel">Medya Paneli</div>
      <div id="center-panel">Preview</div>
      <div id="right-panel">AI Chat</div>
    </div>
    <div id="timeline-panel">Timeline</div>
  </div>
  <script src="app.js"></script>
</body>
</html>
```

---

## 5.4 — WebSocket Bağlantı Yöneticisi

`electron/renderer/app.js`:

```javascript
class AgentConnection {
  constructor(url) {
    this.url = url
    this.ws  = null
    this.reconnectDelay = 2000
    this.handlers = {}
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('[ws] Bağlandı')
        document.getElementById('connection-status')?.classList
          .replace('disconnected', 'connected')
        this.reconnectDelay = 2000
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this._dispatch(data)
        } catch (e) {
          console.error('[ws] Parse hatası:', e)
        }
      }

      this.ws.onclose = () => {
        console.warn('[ws] Bağlantı kesildi, yeniden bağlanılıyor...')
        document.getElementById('connection-status')?.classList
          .replace('connected', 'disconnected')
        setTimeout(() => this.connect(), this.reconnectDelay)
        this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 10000)
      }

      this.ws.onerror = (e) => console.error('[ws] Hata:', e)

    } catch (e) {
      console.error('[ws] Bağlantı hatası:', e)
      setTimeout(() => this.connect(), this.reconnectDelay)
    }
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
      return true
    }
    console.warn('[ws] Bağlı değil, mesaj gönderilemedi')
    return false
  }

  on(type, handler) { this.handlers[type] = handler }

  _dispatch(data) {
    const handler = this.handlers[data.type] || this.handlers['*']
    if (handler) handler(data)
    else console.log('[ws] İşlenmemiş mesaj:', data.type, data)
  }
}

// Global bağlantı
const agent = new AgentConnection(window.electronAPI?.agentWsUrl() || 'ws://localhost:8765/ws')

agent.on('progress', (d) => console.log('[progress]', d.tool, d.status))
agent.on('result',   (d) => console.log('[result]', d.text?.slice(0,100)))
agent.on('error',    (d) => console.error('[error]', d.message))

agent.connect()
```

---

## Doğrulama Kontrolleri

```bash
# 1. Electron başlatma testi
npm start

# Beklenen: Pencere açılır, devtools'da "[ws] Bağlandı" görünür
# Agent terminalde "Electron bağlandı" yazar

# 2. Bağlantı durumu kontrolü
# Tarayıcı konsolunda:
# agent.ws.readyState === 1  (OPEN)
```

---

## Geçiş Kriteri

- `npm start` hatasız çalışıyor
- Pencere açılıyor
- Agent otomatik başlatılıyor
- WebSocket bağlantısı kuruluyor (yeşil nokta)
- Devtools konsolunda bağlantı mesajı var

Geçildiyse PHASE_6_UI.md'ye geç.
