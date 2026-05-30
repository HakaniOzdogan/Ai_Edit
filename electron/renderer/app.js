// ── WebSocket Bağlantı Yöneticisi ─────────────────────────────────────────────
class AgentConnection {
  constructor(url) {
    this.url            = url
    this.ws             = null
    this.reconnectDelay = 2000
    this.handlers       = {}
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('[ws] Bağlandı')
        setConnectionStatus(true)
        this.reconnectDelay = 2000
        addSystemMessage('Agent bağlandı ✓')
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
        setConnectionStatus(false)
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
    console.warn('[ws] Bağlı değil')
    return false
  }

  on(type, handler) { this.handlers[type] = handler }

  _dispatch(data) {
    const handler = this.handlers[data.type] || this.handlers['*']
    if (handler) handler(data)
    else console.log('[ws] İşlenmemiş:', data.type, data)
  }
}

// ── Durum Göstergesi ──────────────────────────────────────────────────────────
function setConnectionStatus(connected) {
  const dot   = document.getElementById('connection-status')
  const label = document.getElementById('connection-label')
  if (!dot) return
  dot.className   = 'status-dot ' + (connected ? 'connected' : 'disconnected')
  label.textContent = connected ? 'Bağlı' : 'Bağlanıyor...'
}

// ── Progress Bar ──────────────────────────────────────────────────────────────
const TOOL_PROGRESS = {
  claude_thinking: { pct: 5,  label: 'Claude düşünüyor...' },
  analyze_music:   { pct: 25, label: 'Müzik analiz ediliyor...' },
  score_clips:     { pct: 45, label: 'Klipler puanlanıyor...' },
  build_timeline:  { pct: 65, label: 'Kurgu oluşturuluyor...' },
  run_ffmpeg:      { pct: 85, label: 'Render alınıyor...' },
}

function updateProgress(data) {
  const bar   = document.getElementById('progress-bar')
  const label = document.getElementById('progress-label')
  if (!bar || !label) return
  const info = TOOL_PROGRESS[data.tool || data.step] || { pct: 50, label: data.message || 'İşleniyor...' }
  bar.style.width   = info.pct + '%'
  label.textContent = info.label
}

function resetProgress(msg = 'Hazır') {
  const bar   = document.getElementById('progress-bar')
  const label = document.getElementById('progress-label')
  if (bar)   bar.style.width   = '0%'
  if (label) label.textContent = msg
}

// ── Chat Paneli ───────────────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function addMessage(role, text) {
  const box = document.getElementById('chat-messages')
  if (!box) return
  const div = document.createElement('div')
  div.className = `message message-${role}`
  div.textContent = text
  box.appendChild(div)
  box.scrollTop = box.scrollHeight
}

function addSystemMessage(text) {
  addMessage('system', text)
}

// ── Medya Listesi ─────────────────────────────────────────────────────────────
const state = { clips: [], photos: [], music: null, logo: null }

function addMediaItem(filePath) {
  const ext  = filePath.split('.').pop().toLowerCase()
  const name = filePath.split(/[\\/]/).pop()

  if (['mp4','mov','avi','mkv'].includes(ext)) {
    if (!state.clips.includes(filePath)) state.clips.push(filePath)
  } else if (['jpg','jpeg','png','webp'].includes(ext)) {
    if (!state.photos.includes(filePath)) state.photos.push(filePath)
  } else if (['mp3','wav','aac','flac'].includes(ext)) {
    state.music = filePath
    const info = document.getElementById('music-info')
    if (info) info.textContent = '🎵 ' + name
  }

  renderMediaList()
  updateRenderButtons()
}

function renderMediaList() {
  const list = document.getElementById('media-list')
  if (!list) return
  list.innerHTML = ''
  ;[...state.clips, ...state.photos].forEach(p => {
    const item = document.createElement('div')
    item.className = 'media-item'
    item.textContent = p.split(/[\\/]/).pop()
    list.appendChild(item)
  })
}

function updateRenderButtons() {
  const hasMedia = state.clips.length > 0 || state.photos.length > 0
  const btn = document.getElementById('btn-demo')
  if (btn) btn.disabled = !hasMedia
}

// ── Drag & Drop ───────────────────────────────────────────────────────────────
function setupDropZones() {
  const zones = [
    document.getElementById('drop-zone'),
    document.getElementById('music-zone')
  ]

  zones.forEach(zone => {
    if (!zone) return
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over') })
    zone.addEventListener('dragleave', ()  => zone.classList.remove('drag-over'))
    zone.addEventListener('drop', e => {
      e.preventDefault()
      zone.classList.remove('drag-over')
      Array.from(e.dataTransfer.files).forEach(f => addMediaItem(f.path))
    })
  })
}

// ── Komut Gönderme ────────────────────────────────────────────────────────────
function sendCommand(command) {
  if (!command.trim()) return
  addMessage('user', command)

  const ok = agent.send({
    type:       'command',
    command,
    project_id: 'proj_' + Date.now(),
    style:      'dark',
    files: {
      clips:  state.clips,
      photos: state.photos,
      music:  state.music,
      logo:   state.logo
    }
  })

  if (!ok) addSystemMessage('Agent bağlı değil, tekrar denenecek...')
}

// ── Agent Mesaj Handler'ları ──────────────────────────────────────────────────
const agent = new AgentConnection(
  window.electronAPI?.agentWsUrl() || 'ws://localhost:8765/ws'
)

agent.on('progress', (d) => {
  updateProgress(d)
  if (d.message) addSystemMessage(d.message)
})

agent.on('result', (d) => {
  resetProgress('Tamamlandı')
  addMessage('assistant', d.text || '')
  document.getElementById('btn-final').disabled = false
})

agent.on('error', (d) => {
  resetProgress('Hata')
  addSystemMessage('Hata: ' + (d.message || 'Bilinmeyen hata'))
})

// ── Event Listener'lar ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupDropZones()

  // Chat input
  const sendBtn   = document.getElementById('send-btn')
  const chatInput = document.getElementById('chat-input')

  sendBtn?.addEventListener('click', () => {
    sendCommand(chatInput.value)
    chatInput.value = ''
  })

  chatInput?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendCommand(chatInput.value)
      chatInput.value = ''
    }
  })

  // Hızlı komut butonları
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => sendCommand(btn.dataset.cmd))
  })

  // Demo buton
  document.getElementById('btn-demo')?.addEventListener('click', () => {
    sendCommand('Demo oluştur — dark cinematic tarz')
  })

  agent.connect()
})
