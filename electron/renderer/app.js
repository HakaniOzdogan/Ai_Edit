// ── WebSocket Bağlantı Yöneticisi ─────────────────────────────────────────────
class AgentConnection {
  constructor(url) {
    this.url = url; this.ws = null
    this.reconnectDelay = 2000; this.handlers = {}
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url)
      this.ws.onopen    = () => { setStatus(true); this.reconnectDelay = 2000 }
      this.ws.onmessage = e  => { try { this._dispatch(JSON.parse(e.data)) } catch(err) { console.error('[ws parse]', err) } }
      this.ws.onclose   = () => {
        setStatus(false)
        setTimeout(() => this.connect(), this.reconnectDelay)
        this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 10000)
      }
      this.ws.onerror = e => console.error('[ws]', e)
    } catch (e) {
      setTimeout(() => this.connect(), this.reconnectDelay)
    }
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) { this.ws.send(JSON.stringify(data)); return true }
    return false
  }

  on(type, fn) { this.handlers[type] = fn }

  _dispatch(data) {
    const h = this.handlers[data.type] || this.handlers['*']
    if (h) h(data); else console.log('[ws unhandled]', data.type)
  }
}

// ── Durum ─────────────────────────────────────────────────────────────────────
function setStatus(on) {
  const dot = document.getElementById('connection-status')
  const lbl = document.getElementById('connection-label')
  if (dot) dot.className = 'status-dot ' + (on ? 'connected' : 'disconnected')
  if (lbl) lbl.textContent = on ? 'Bağlı' : 'Bağlanıyor...'
  if (on) chat.addSystem('Agent bağlandı ✓')
}

// ── Progress Bar ──────────────────────────────────────────────────────────────
const TOOL_STEPS = {
  claude_thinking: { p: 5,  l: 'Claude düşünüyor...' },
  direct_render:   { p: 10, l: 'Render başlatılıyor...' },
  analyze_music:   { p: 25, l: 'Müzik analiz ediliyor...' },
  score_clips:     { p: 45, l: 'Klipler puanlanıyor...' },
  build_timeline:  { p: 60, l: 'Kurgu oluşturuluyor...' },
  run_ffmpeg:      { p: 80, l: 'Render alınıyor...' },
  render_timeline: { p: 80, l: 'Video render ediliyor...' },
  qa:              { p: 92, l: 'Kalite kontrol yapılıyor...' },
}

function setProgress(data) {
  const info = TOOL_STEPS[data.tool || data.step]
  const bar  = document.getElementById('progress-bar')
  const lbl  = document.getElementById('progress-label')
  if (bar) bar.style.width = (info?.p || 50) + '%'
  if (lbl) lbl.textContent = info?.l || data.message || 'İşleniyor...'
}

function resetProgress(msg = 'Hazır') {
  const bar = document.getElementById('progress-bar')
  const lbl = document.getElementById('progress-label')
  if (bar) bar.style.width = '0%'
  if (lbl) lbl.textContent = msg
}

// ── QA Paneli ─────────────────────────────────────────────────────────────────
const GRADE_COLORS = { A: '#4ade80', B: '#60a5fa', C: '#fbbf24', D: '#f97316', F: '#ef4444', '?': '#888' }

function showQAResult(score, grade, report) {
  const wrap  = document.getElementById('qa-result')
  const badge = document.getElementById('qa-grade-badge')
  const label = document.getElementById('qa-score-label')
  const issues = document.getElementById('qa-issues')
  const suggestions = document.getElementById('qa-suggestions')
  if (!wrap) return

  wrap.style.display = 'block'
  badge.textContent  = grade || '?'
  badge.style.background = GRADE_COLORS[grade] || '#888'
  label.textContent  = score != null ? `QA: ${score.toFixed(1)} / 100` : 'QA: —'

  if (issues && report?.issues?.length) {
    issues.innerHTML = report.issues.map(i => `<li>⚠ ${i}</li>`).join('')
  }
  if (suggestions && report?.suggestions?.length) {
    suggestions.innerHTML = report.suggestions.map(s => `<li>💡 ${s}</li>`).join('')
  }
}

// ── Chat Paneli ───────────────────────────────────────────────────────────────
const chat = {
  _box() { return document.getElementById('chat-messages') },

  add(role, text) {
    const box = this._box(); if (!box) return
    const el = document.createElement('div')
    el.className = 'message message-' + role
    el.textContent = text
    box.appendChild(el)
    box.scrollTop = box.scrollHeight
  },

  addUser(text)      { this.add('user', text) },
  addAssistant(text) { this.add('assistant', text) },
  addSystem(text)    { this.add('system', text) },
  addProgress(text)  { this.add('progress', '⚙ ' + text) },
  addError(text)     { this.add('error', '✖ ' + text) },
}

// ── Tema Toggle ───────────────────────────────────────────────────────────────
function toggleTheme() {
  const html    = document.documentElement
  const current = html.getAttribute('data-theme') || 'dark'
  const next    = current === 'dark' ? 'light' : 'dark'
  html.setAttribute('data-theme', next)
  localStorage.setItem('theme', next)
  const btn = document.getElementById('theme-toggle')
  if (btn) btn.textContent = next === 'dark' ? '☀' : '🌙'
}

// ── Timeline Render ───────────────────────────────────────────────────────────
function renderTimeline(timeline) {
  const track = document.getElementById('timeline-track')
  if (!track || !timeline?.length) return
  track.innerHTML = ''
  timeline.forEach((seg, i) => {
    const el = document.createElement('div')
    el.className = 'timeline-seg'
    const name = seg.clip_path?.split(/[\\/]/).pop() || `Klip ${i+1}`
    el.innerHTML = `<span>${name.slice(0,12)}</span><span class="seg-dur">${seg.duration?.toFixed(1)}s</span>`
    el.style.minWidth = Math.max(60, seg.duration * 18) + 'px'
    track.appendChild(el)
  })
}

// ── Video Player ──────────────────────────────────────────────────────────────
function loadVideo(filePath) {
  const player = document.getElementById('preview-player')
  const ph     = document.getElementById('player-placeholder')
  if (!player) return
  player.src = 'file:///' + filePath.replace(/\\/g, '/')
  player.style.display = 'block'
  if (ph) ph.style.display = 'none'
  player.load()
  document.getElementById('btn-final').disabled = false
}

// ── Medya State ───────────────────────────────────────────────────────────────
const media = { clips: [], photos: [], music: null, logo: null }

function addFile(path) {
  const ext  = path.split('.').pop().toLowerCase()
  const name = path.split(/[\\/]/).pop()
  if (['mp4','mov','avi','mkv'].includes(ext) && !media.clips.includes(path)) media.clips.push(path)
  else if (['jpg','jpeg','png','webp'].includes(ext) && !media.photos.includes(path)) media.photos.push(path)
  else if (['mp3','wav','aac','flac'].includes(ext)) {
    media.music = path
    const el = document.getElementById('music-info')
    if (el) el.textContent = '🎵 ' + name
  }
  renderMediaList()
  document.getElementById('btn-demo').disabled = !(media.clips.length || media.photos.length)
}

function renderMediaList() {
  const list = document.getElementById('media-list'); if (!list) return
  list.innerHTML = ''
  media.clips.forEach(p  => addItem(list, p, 'clip'))
  media.photos.forEach(p => addItem(list, p, 'photo'))
}

function addItem(list, path, type) {
  const el = document.createElement('div')
  el.className = 'media-item ' + type
  el.textContent = path.split(/[\\/]/).pop()
  el.title = path
  list.appendChild(el)
}

// ── Deterministik Render Komutları ────────────────────────────────────────────
window.currentProjectId = 'proj_' + Date.now()

function sendRender(renderType) {
  const label = renderType === 'final' ? '4K Final render başlatılıyor...' : 'Demo render başlatılıyor...'
  chat.addSystem(label)
  const ok = agent.send({
    type:        'command',
    command:     renderType === 'final' ? 'Final 4K render al' : 'Demo oluştur',
    render_type: renderType,
    project_id:  window.currentProjectId,
    style:       window.currentStyle || 'dark',
    files: { clips: media.clips, photos: media.photos, music: media.music, logo: media.logo }
  })
}

function sendCommand(cmd) {
  cmd = (cmd || '').slice(0, 500).trim()
  if (!cmd) return
  // Hızlı komut kısayolları
  if (cmd === 'demo')  return sendRender('demo')
  if (cmd === 'final') return sendRender('final')
  chat.addUser(cmd)
  agent.send({
    type: 'command', command: cmd,
    project_id: window.currentProjectId,
    style: window.currentStyle || 'dark',
    files: { clips: media.clips, photos: media.photos, music: media.music, logo: media.logo }
  })
}

// ── Proje Kaydet / Yükle ──────────────────────────────────────────────────────
async function saveProject() {
  const projectData = {
    project_id: window.currentProjectId,
    style:      window.currentStyle || 'dark',
    files:      { clips: media.clips, photos: media.photos, music: media.music, logo: media.logo },
  }
  try {
    const res = await fetch(
      (window.electronAPI?.agentHttpUrl() || 'http://localhost:8765') + '/projects',
      { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(projectData) }
    )
    const data = await res.json()
    if (data.ok) chat.addSystem(`Proje kaydedildi: ${data.project_id}`)
    else chat.addError('Proje kaydedilemedi')
  } catch (e) {
    chat.addError('Kaydetme hatası: ' + e.message)
  }
}

async function loadProject() {
  try {
    const base = window.electronAPI?.agentHttpUrl() || 'http://localhost:8765'
    const res  = await fetch(base + '/projects')
    const data = await res.json()
    if (!data.projects?.length) { chat.addSystem('Kayıtlı proje yok'); return }

    const id = prompt('Proje ID:\n' + data.projects.join('\n'))
    if (!id) return

    const projRes  = await fetch(base + '/projects/' + id)
    const projData = await projRes.json()

    window.currentProjectId = projData.project_id
    window.currentStyle     = projData.style || 'dark'
    if (projData.files) {
      media.clips  = projData.files.clips  || []
      media.photos = projData.files.photos || []
      media.music  = projData.files.music  || null
      media.logo   = projData.files.logo   || null
      renderMediaList()
      if (media.music) {
        const el = document.getElementById('music-info')
        if (el) el.textContent = '🎵 ' + media.music.split(/[\\/]/).pop()
      }
    }
    document.getElementById('btn-demo').disabled = !(media.clips.length || media.photos.length)
    chat.addSystem(`Proje yüklendi: ${id}`)
  } catch (e) {
    chat.addError('Yükleme hatası: ' + e.message)
  }
}

// ── Agent Bağlantısı ──────────────────────────────────────────────────────────
const agent = new AgentConnection(
  window.electronAPI?.agentWsUrl() || 'ws://localhost:8765/ws'
)

agent.on('progress', d => {
  setProgress(d)
  if (d.message) chat.addProgress(d.message)
})

agent.on('result', d => {
  resetProgress('Tamamlandı ✓')
  if (d.text) chat.addAssistant(d.text)
  if (d.output_path) loadVideo(d.output_path)
  if (d.timeline)    renderTimeline(d.timeline)
  if (d.qa_score != null || d.qa_grade) {
    showQAResult(d.qa_score, d.qa_grade, d.qa_report)
    const passLabel = d.qa_pass ? '✓ QA Geçti' : '✗ QA Başarısız'
    chat.addSystem(`QA: ${d.qa_grade || '?'} — ${d.qa_score?.toFixed(1) || '—'} / 100 — ${passLabel}`)
  }
})

agent.on('error', d => {
  resetProgress('Hata')
  chat.addError(d.message || 'Bilinmeyen hata')
})

// ── Sihirbaz ──────────────────────────────────────────────────────────────────
function openWizard() {
  const wiz = new ProjectWizard(config => {
    window.currentProjectId = config.projectId
    window.currentStyle     = config.style
    Object.assign(media, { clips: config.clips, photos: config.photos,
                            music: config.music, logo: config.logo })
    renderMediaList()
    if (config.music) {
      const el = document.getElementById('music-info')
      if (el) el.textContent = '🎵 ' + config.music.split(/[\\/]/).pop()
    }
    document.getElementById('btn-demo').disabled = !(media.clips.length || media.photos.length)
    sendRender('demo')
  })
  wiz.setMedia(media.clips, media.photos, media.music, media.logo)
}

// ── Event Listener'lar ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Kayıtlı temayı uygula
  const savedTheme = localStorage.getItem('theme') || 'dark'
  document.documentElement.setAttribute('data-theme', savedTheme)
  const themeBtn = document.getElementById('theme-toggle')
  if (themeBtn) themeBtn.textContent = savedTheme === 'dark' ? '☀' : '🌙'

  // Drag & Drop — medya
  const dropZone = document.getElementById('drop-zone')
  dropZone?.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over') })
  dropZone?.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'))
  dropZone?.addEventListener('drop', e => {
    e.preventDefault(); dropZone.classList.remove('drag-over')
    Array.from(e.dataTransfer.files).forEach(f => addFile(f.path))
  })

  // Drag & Drop — müzik
  const musicZone = document.getElementById('music-zone')
  musicZone?.addEventListener('dragover', e => { e.preventDefault(); musicZone.classList.add('drag-over') })
  musicZone?.addEventListener('dragleave', () => musicZone.classList.remove('drag-over'))
  musicZone?.addEventListener('drop', e => {
    e.preventDefault(); musicZone.classList.remove('drag-over')
    const f = e.dataTransfer.files[0]; if (f) addFile(f.path)
  })

  // Chat
  const sendBtn = document.getElementById('send-btn')
  const input   = document.getElementById('chat-input')
  sendBtn?.addEventListener('click', () => { sendCommand(input.value); input.value = '' })
  input?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendCommand(input.value); input.value = '' }
  })

  // Hızlı komut butonları
  document.querySelectorAll('.quick-btn').forEach(b =>
    b.addEventListener('click', () => sendCommand(b.dataset.cmd)))

  // Deterministik render butonları
  document.getElementById('btn-demo')?.addEventListener('click',  () => sendRender('demo'))
  document.getElementById('btn-final')?.addEventListener('click', () => sendRender('final'))

  // Titlebar butonları
  document.getElementById('btn-wizard')?.addEventListener('click',       openWizard)
  document.getElementById('theme-toggle')?.addEventListener('click',     toggleTheme)
  document.getElementById('btn-save-project')?.addEventListener('click', saveProject)
  document.getElementById('btn-load-project')?.addEventListener('click', loadProject)

  // QA detay toggle
  document.getElementById('qa-toggle-detail')?.addEventListener('click', () => {
    const d = document.getElementById('qa-detail')
    if (d) d.style.display = d.style.display === 'none' ? 'block' : 'none'
  })

  agent.connect()
})
