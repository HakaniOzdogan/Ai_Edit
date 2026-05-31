const BASE = () => window.electronAPI?.agentHttpUrl() || 'http://localhost:8765'

// ── Ekran Geçişleri ───────────────────────────────────────────────────────────
function showHome(askSave = true) {
  // Kaydedilmemiş iş varsa sor
  const hasMedia = media.clips.length > 0 || media.photos.length > 0
  if (askSave && hasMedia) {
    showConfirmModal(
      'Ana Ekrana Dön',
      'Mevcut proje kaybolabilir. Devam etmeden önce kaydetmek ister misin?',
      [
        { label: '💾 Kaydet ve Dön', action: async () => { await saveProject(); _goHome() } },
        { label: '→ Kaydetmeden Dön',  action: _goHome },
        { label: 'İptal',              action: null    },
      ]
    )
    return
  }
  _goHome()
}

function _goHome() {
  document.getElementById('home-screen').style.display   = 'flex'
  document.getElementById('editor-screen').style.display = 'none'
  document.getElementById('home-ready-msg')?.remove()
  if (agent.ws?.readyState === WebSocket.OPEN) loadRecentProjects()
}

function resetProjectState() {
  // Tüm proje state'ini sıfırla — yeni proje için temiz başlangıç
  media.clips  = []
  media.photos = []
  media.music  = null
  media.logo   = null

  // UI temizle
  renderMediaList()
  const musicInfo = document.getElementById('music-info')
  const logoInfo  = document.getElementById('logo-info')
  const musicUrl  = document.getElementById('music-url-status')
  const videoWrap = document.getElementById('preview-player')
  const ph        = document.getElementById('player-placeholder')
  const timeline  = document.getElementById('timeline-track')
  const qaResult  = document.getElementById('qa-result')
  const chatBox   = document.getElementById('chat-messages')

  if (musicInfo) musicInfo.textContent = ''
  if (logoInfo)  logoInfo.textContent  = ''
  if (musicUrl)  musicUrl.textContent  = ''
  if (videoWrap) { videoWrap.src = ''; videoWrap.style.display = 'none' }
  if (ph)        ph.style.display = 'block'
  if (timeline)  timeline.innerHTML = ''
  if (qaResult)  qaResult.style.display = 'none'
  if (chatBox)   chatBox.innerHTML = ''

  // Progress sıfırla
  resetProgress('Hazır')

  // Butonları sıfırla
  const btnDemo  = document.getElementById('btn-demo')
  const btnFinal = document.getElementById('btn-final')
  if (btnDemo)  btnDemo.disabled  = true
  if (btnFinal) btnFinal.disabled = true

  // Yeni proje ID
  window.currentProjectId = 'proj_' + Date.now()
  window.currentStyle     = 'dark'
  updateToolbar()
}

function showEditor() {
  document.getElementById('home-screen').style.display   = 'none'
  document.getElementById('editor-screen').style.display = 'block'
}

// ── Ana Ekran ─────────────────────────────────────────────────────────────────
async function loadRecentProjects() {
  const list = document.getElementById('home-recent-list')
  try {
    const res  = await fetch(BASE() + '/projects', { signal: AbortSignal.timeout(3000) })
    const data = await res.json()
    if (!data.projects?.length) {
      list.innerHTML = '<div class="home-recent-empty">Henüz kayıtlı proje yok</div>'
      return
    }
    list.innerHTML = data.projects.slice(0, 6).map(id => `
      <div class="home-recent-item" data-id="${id}">
        <span class="home-recent-icon">🎬</span>
        <span class="home-recent-name">${id}</span>
        <button class="home-recent-del" data-del="${id}" title="Sil">✕</button>
      </div>`).join('')

    list.querySelectorAll('.home-recent-item').forEach(el => {
      el.addEventListener('click', e => {
        if (e.target.dataset.del) return
        openProjectById(el.dataset.id)
      })
    })
    list.querySelectorAll('.home-recent-del').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation()
        await fetch(BASE() + '/projects/' + btn.dataset.del, { method: 'DELETE' })
        loadRecentProjects()
      })
    })
  } catch {
    list.innerHTML = '<div class="home-recent-empty">Agent bağlantısı bekleniyor...</div>'
  }
}

async function openProjectById(id) {
  try {
    resetProjectState()   // Önce temizle
    const res  = await fetch(BASE() + '/projects/' + id)
    const data = await res.json()
    applyProjectData(data)
    showEditor()
  } catch (e) {
    console.error('Proje açılamadı:', e)
  }
}

function applyProjectData(projData) {
  window.currentProjectId = projData.project_id
  window.currentStyle     = projData.style || 'dark'
  if (projData.files) {
    media.clips  = projData.files.clips  || []
    media.photos = projData.files.photos || []
    media.music  = projData.files.music  || null
    media.logo   = projData.files.logo   || null
    renderMediaList()
    if (media.music) updateMusicInfo(media.music)
    if (media.logo)  updateLogoInfo(media.logo)
  }
  updateToolbar()
  document.getElementById('btn-demo').disabled  = !(media.clips.length || media.photos.length)
  document.getElementById('btn-final').disabled = true
}

// ── Proje Modal (prompt() yerine) ────────────────────────────────────────────
async function showProjectModal() {
  const modal = document.getElementById('project-modal')
  const list  = document.getElementById('project-modal-list')
  const empty = document.getElementById('project-modal-empty')

  modal.style.display = 'flex'
  list.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text-muted)">Yükleniyor...</div>'
  empty.style.display = 'none'

  try {
    const res  = await fetch(BASE() + '/projects')
    const data = await res.json()

    if (!data.projects?.length) {
      list.innerHTML = ''
      empty.style.display = 'block'
      return
    }

    list.innerHTML = data.projects.map(id => `
      <div class="project-modal-item" data-id="${id}">
        <span class="project-modal-item-icon">🎬</span>
        <div class="project-modal-item-info">
          <div class="project-modal-item-name">${id}</div>
          <div class="project-modal-item-meta">Kayıtlı proje</div>
        </div>
        <button class="project-modal-item-del" data-del="${id}" title="Sil">🗑</button>
      </div>`).join('')

    list.querySelectorAll('.project-modal-item').forEach(el => {
      el.addEventListener('click', e => {
        if (e.target.dataset.del) return
        modal.style.display = 'none'
        openProjectById(el.dataset.id)
        if (document.getElementById('home-screen').style.display !== 'none') showEditor()
      })
    })
    list.querySelectorAll('.project-modal-item-del').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation()
        await fetch(BASE() + '/projects/' + btn.dataset.del, { method: 'DELETE' })
        showProjectModal()
      })
    })
  } catch (e) {
    list.innerHTML = `<div style="padding:16px;text-align:center;color:var(--error)">Bağlantı hatası: ${e.message}</div>`
  }
}

// ── Toolbar Güncelle ──────────────────────────────────────────────────────────
function updateToolbar() {
  const nameEl  = document.getElementById('tb-project-name')
  const styleEl = document.getElementById('tb-project-style')
  if (nameEl)  nameEl.textContent  = window.currentProjectId || 'Yeni Proje'
  if (styleEl) styleEl.textContent = window.currentStyle || 'dark'
}

// ── Startup Loading Animasyonu ────────────────────────────────────────────────
let _startupTimer   = null
let _startupElapsed = 0
const STARTUP_STEPS = [
  { at:  0, pct:  5, msg: 'Başlatılıyor...',          sub: 'Python ortamı hazırlanıyor' },
  { at:  3, pct: 20, msg: 'FastAPI sunucu yükleniyor', sub: '~15 saniye sürebilir' },
  { at:  6, pct: 40, msg: 'AI kütüphaneleri yükleniyor', sub: 'librosa, opencv başlatılıyor' },
  { at: 10, pct: 60, msg: 'Neredeyse hazır...',        sub: 'Son modüller yükleniyor' },
  { at: 14, pct: 80, msg: 'Bağlantı bekleniyor...',    sub: 'Agent hazırlanıyor' },
  { at: 20, pct: 90, msg: 'Biraz daha bekle...',       sub: 'İlk başlatma uzun sürebilir' },
  { at: 30, pct: 95, msg: 'Hâlâ yükleniyor...',        sub: 'Büyük proje yüklenirken normaldir' },
]

function startLoadingAnimation() {
  _startupElapsed = 0

  const fill  = document.getElementById('home-progress-fill')
  const label = document.getElementById('home-agent-label')
  const sub   = document.getElementById('home-loading-sub')
  const eta   = document.getElementById('home-eta')
  const btns  = document.getElementById('home-actions')

  // Başlangıç durumu
  if (fill)  { fill.style.transition = 'none'; fill.style.width = '0%' }
  if (label) label.textContent = 'Başlatılıyor...'
  if (sub)   sub.textContent   = 'Python ortamı hazırlanıyor'
  if (eta)   eta.textContent   = '~25 saniye'
  if (btns)  { btns.style.opacity = '0.4'; btns.style.pointerEvents = 'none' }

  // Bir frame bekle, sonra transition'ı aç
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (fill) fill.style.transition = 'width 0.8s ease, background 0.4s'
    })
  })

  if (_startupTimer) clearInterval(_startupTimer)
  _startupTimer = setInterval(() => {
    _startupElapsed++
    const step = [...STARTUP_STEPS].reverse().find(s => _startupElapsed >= s.at)
    if (!step) return
    if (fill)  fill.style.width  = step.pct + '%'
    if (label) label.textContent = step.msg
    if (sub)   sub.textContent   = step.sub
    if (eta) {
      const rem = Math.max(0, 25 - _startupElapsed)
      eta.textContent = rem > 0 ? ('~' + rem + ' saniye') : 'Neredeyse hazir...'
    }
  }, 1000)
}

function stopLoadingAnimation() {
  if (_startupTimer) { clearInterval(_startupTimer); _startupTimer = null }
  const fill  = document.getElementById('home-progress-fill')
  const label = document.getElementById('home-agent-label')
  const sub   = document.getElementById('home-loading-sub')
  const eta   = document.getElementById('home-eta')
  const spin  = document.getElementById('home-spinner')
  const wrap  = document.getElementById('home-loading-wrap')
  const btns  = document.getElementById('home-actions')

  if (fill)  { fill.style.width = '100%'; fill.style.background = 'var(--accent-green)' }
  if (spin)  {
    spin.style.animation   = 'none'
    spin.style.border      = '2px solid var(--accent-green)'
    spin.style.borderRadius = '50%'
    spin.style.background  = 'var(--accent-green)'
  }
  if (label) label.textContent = 'Sistem hazır!'
  if (sub)   sub.textContent   = `${_startupElapsed} saniyede yüklendi`
  if (eta)   eta.textContent   = ''

  // "Hazırız" büyük mesajı göster
  const statusEl = document.getElementById('home-status')
  if (statusEl) {
    const readyMsg = document.createElement('div')
    readyMsg.id = 'home-ready-msg'
    readyMsg.textContent = 'Hazırız — Başlayalım!'
    statusEl.appendChild(readyMsg)
    requestAnimationFrame(() => readyMsg.classList.add('visible'))
  }
  if (btns)  btns.style.opacity    = '1'
  if (btns)  btns.style.pointerEvents = 'auto'
  setTimeout(() => {
    const s = document.getElementById('home-status')
    if (s) s.style.opacity = '0.5'
  }, 3000)
}

function setStatus(on) {
  const dot   = document.getElementById('connection-status')
  const label = document.getElementById('connection-label')
  const hdot  = document.getElementById('home-agent-dot')
  const cls   = 'status-dot ' + (on ? 'connected' : 'disconnected')
  if (dot)  dot.className  = cls
  if (label) label.textContent = on ? 'Bağlı' : 'Bağlanıyor'
  if (hdot) hdot.className = cls
  if (on) {
    stopLoadingAnimation()
    loadRecentProjects()
    chat.addSystem('Agent bağlandı ✓')
  }
}

// ── Progress Bar ──────────────────────────────────────────────────────────────
const TOOL_STEPS = {
  claude_thinking: { p: 5,  l: 'Claude düşünüyor...' },
  direct_render:   { p: 10, l: 'Render başlatılıyor...' },
  analyze_music:   { p: 22, l: 'Müzik analiz ediliyor...' },
  score_clips:     { p: 40, l: 'Klipler puanlanıyor...' },
  build_timeline:  { p: 58, l: 'Kurgu oluşturuluyor...' },
  render_timeline: { p: 75, l: 'Video render ediliyor...' },
  run_ffmpeg:      { p: 75, l: 'FFmpeg çalışıyor...' },
  color_grade:     { p: 85, l: 'Renk düzeltiliyor...' },
  add_logo:        { p: 90, l: 'Logo ekleniyor...' },
  add_text:        { p: 92, l: 'Metin ekleniyor...' },
  qa:              { p: 95, l: 'Kalite kontrol...' },
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
const GRADE_COLORS = { A:'#4ade80', B:'#60a5fa', C:'#fbbf24', D:'#f97316', F:'#ef4444', '?':'#888' }

function showQAResult(score, grade, report) {
  const wrap  = document.getElementById('qa-result')
  const badge = document.getElementById('qa-grade-badge')
  const label = document.getElementById('qa-score-label')
  const issues = document.getElementById('qa-issues')
  const sugg   = document.getElementById('qa-suggestions')
  if (!wrap) return
  wrap.style.display = 'block'
  badge.textContent  = grade || '?'
  badge.style.background = GRADE_COLORS[grade] || '#888'
  label.textContent  = score != null ? `QA: ${Number(score).toFixed(1)} / 100` : 'QA: —'
  if (issues && report?.issues?.length)
    issues.innerHTML = report.issues.map(i => `<li>⚠ ${i}</li>`).join('')
  if (sugg && report?.suggestions?.length)
    sugg.innerHTML = report.suggestions.map(s => `<li>💡 ${s}</li>`).join('')
}

// ── Chat Paneli ───────────────────────────────────────────────────────────────
const chat = {
  _box() { return document.getElementById('chat-messages') },
  add(role, text) {
    const box = this._box(); if (!box) return
    const el  = document.createElement('div')
    el.className  = 'message message-' + role
    el.textContent = text
    box.appendChild(el)
    box.scrollTop = box.scrollHeight
  },
  addUser(t)      { this.add('user', t) },
  addAssistant(t) { this.add('assistant', t) },
  addSystem(t)    { this.add('system', t) },
  addProgress(t)  { this.add('progress', '⚙ ' + t) },
  addError(t)     { this.add('error', '✕ ' + t) },
  clear()         { const b = this._box(); if (b) b.innerHTML = '' },
}

// ── Timeline ──────────────────────────────────────────────────────────────────
function renderTimeline(timeline) {
  const track = document.getElementById('timeline-track')
  const info  = document.getElementById('timeline-info')
  if (!track || !timeline?.length) return
  track.innerHTML = ''
  timeline.forEach((seg, i) => {
    const el   = document.createElement('div')
    el.className = 'timeline-seg'
    const name = seg.clip_path?.split(/[\\/]/).pop() || `Klip ${i+1}`
    el.innerHTML = `<span>${name.slice(0,12)}</span><span class="seg-dur">${Number(seg.duration).toFixed(1)}s</span>`
    el.style.minWidth = Math.max(60, seg.duration * 18) + 'px'
    track.appendChild(el)
  })
  if (info) info.textContent = `${timeline.length} sahne`
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
  if (['mp4','mov','avi','mkv'].includes(ext) && !media.clips.includes(path))
    media.clips.push(path)
  else if (['jpg','jpeg','png','webp'].includes(ext) && !media.photos.includes(path))
    media.photos.push(path)
  else if (['mp3','wav','aac','flac'].includes(ext)) {
    media.music = path; updateMusicInfo(path)
  } else if (ext === 'png' && path.toLowerCase().includes('logo')) {
    media.logo = path; updateLogoInfo(path)
  }
  renderMediaList()
  document.getElementById('btn-demo').disabled = !(media.clips.length || media.photos.length)
}

function updateMusicInfo(path) {
  const el = document.getElementById('music-info')
  if (el) el.textContent = '🎵 ' + path.split(/[\\/]/).pop()
}

function updateLogoInfo(path) {
  const el = document.getElementById('logo-info')
  if (el) el.textContent = '🖼 ' + path.split(/[\\/]/).pop()
}

function renderMediaList() {
  const list = document.getElementById('media-list'); if (!list) return
  list.innerHTML = ''
  media.clips.forEach(p  => {
    const el = document.createElement('div')
    el.className = 'media-item clip'
    el.textContent = p.split(/[\\/]/).pop(); el.title = p
    list.appendChild(el)
  })
  media.photos.forEach(p => {
    const el = document.createElement('div')
    el.className = 'media-item photo'
    el.textContent = p.split(/[\\/]/).pop(); el.title = p
    list.appendChild(el)
  })
}

// ── Müzik URL İndirme ─────────────────────────────────────────────────────────
async function downloadMusicFromUrl(url) {
  const statusEl = document.getElementById('music-url-status')
  const btn      = document.getElementById('music-url-btn')
  const base     = window.electronAPI?.agentHttpUrl() || 'http://localhost:8765'

  if (!url.trim()) return
  if (statusEl) statusEl.textContent = '🔍 Parça bilgisi alınıyor...'
  if (btn)      btn.disabled = true

  try {
    // Önce parça bilgisini al
    const infoRes  = await fetch(base + '/music/info', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    })
    const info = await infoRes.json()

    if (!info.ok) {
      if (statusEl) statusEl.textContent = '❌ ' + (info.error || 'Bilgi alınamadı')
      return
    }

    const mins = Math.floor((info.duration || 0) / 60)
    const secs = String(Math.floor((info.duration || 0) % 60)).padStart(2, '0')
    if (statusEl) statusEl.textContent = `⬇ "${info.title}" (${mins}:${secs}) indiriliyor...`

    // İndir
    const dlRes  = await fetch(base + '/music/download', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
      signal: AbortSignal.timeout(180000)  // 3 dk
    })
    const dl = await dlRes.json()

    if (dl.ok && dl.path) {
      media.music = dl.path
      updateMusicInfo(dl.path)
      if (statusEl) statusEl.textContent = `✓ ${info.title} (${dl.size_mb} MB)`
      document.getElementById('btn-demo').disabled = !(media.clips.length || media.photos.length)
      chat.addSystem(`Müzik indirildi: ${info.title}`)
      // Input'u temizle
      const inp = document.getElementById('music-url-input')
      if (inp) inp.value = ''
    } else {
      if (statusEl) statusEl.textContent = '❌ ' + (dl.error || 'İndirme başarısız')
      chat.addError('Müzik indirilemedi: ' + (dl.error || ''))
    }
  } catch (e) {
    if (statusEl) statusEl.textContent = '❌ Hata: ' + e.message
    chat.addError('Müzik indirme hatası: ' + e.message)
  } finally {
    if (btn) btn.disabled = false
  }
}

// ── Proje Kaydet ─────────────────────────────────────────────────────────────
async function saveProject() {
  const data = {
    project_id: window.currentProjectId,
    style:      window.currentStyle || 'dark',
    files:      { clips: media.clips, photos: media.photos, music: media.music, logo: media.logo },
  }
  try {
    const res  = await fetch(BASE() + '/projects', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    const resp = await res.json()
    if (resp.ok) {
      updateToolbar()
      chat.addSystem(`Proje kaydedildi ✓`)
    } else {
      chat.addError('Proje kaydedilemedi')
    }
  } catch (e) { chat.addError('Kaydetme hatası: ' + e.message) }
}

// ── Render Komutları ──────────────────────────────────────────────────────────
window.currentProjectId = 'proj_' + Date.now()
window.currentStyle     = 'dark'

function sendRender(renderType) {
  chat.addSystem(`${renderType === 'final' ? '4K Final' : 'Demo'} render başlatılıyor...`)
  agent.send({
    type: 'command',
    command: renderType === 'final' ? 'Final 4K render al' : 'Demo oluştur',
    render_type: renderType,
    project_id:  window.currentProjectId,
    style:       window.currentStyle || 'dark',
    files: { clips: media.clips, photos: media.photos, music: media.music, logo: media.logo }
  })
}

function sendCommand(cmd) {
  cmd = (cmd || '').slice(0, 500).trim()
  if (!cmd) return
  if (cmd === 'demo')  return sendRender('demo')
  if (cmd === 'final') return sendRender('final')
  chat.addUser(cmd)
  agent.send({
    type: 'command', command: cmd,
    project_id: window.currentProjectId,
    style:       window.currentStyle || 'dark',
    files: { clips: media.clips, photos: media.photos, music: media.music, logo: media.logo }
  })
}

// ── Genel Onay Modalı ─────────────────────────────────────────────────────────
function showConfirmModal(title, message, buttons) {
  document.getElementById('confirm-modal')?.remove()
  const modal = document.createElement('div')
  modal.id = 'confirm-modal'
  const btnsHtml = buttons.map((b, i) =>
    `<button class="btn ${i === 0 ? 'btn-primary' : 'btn-secondary'} btn-sm" data-idx="${i}">${b.label}</button>`
  ).join('')
  modal.innerHTML = `
    <div id="confirm-box">
      <div id="confirm-title">${title}</div>
      <div id="confirm-msg">${message}</div>
      <div id="confirm-btns">${btnsHtml}</div>
    </div>`
  document.body.appendChild(modal)
  modal.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => {
      modal.remove()
      const action = buttons[parseInt(btn.dataset.idx)]?.action
      if (action) action()
    })
  })
}

// ── Plan Onay Diyalogu ────────────────────────────────────────────────────────
let _pendingCommand = null

function showPlanApproval(planText, originalCommand) {
  _pendingCommand = originalCommand
  // Varsa eskiyi kaldır
  document.getElementById('plan-overlay')?.remove()

  const overlay = document.createElement('div')
  overlay.id = 'plan-overlay'
  overlay.innerHTML = `
    <div id="plan-box">
      <div id="plan-header">
        <span id="plan-icon">🎬</span>
        <span id="plan-title">Yapılacaklar</span>
      </div>
      <div id="plan-body">${escapeHtml(planText).replace(/\n/g,'<br>')}</div>
      <div id="plan-footer">
        <button id="plan-approve" class="btn btn-primary">✓ Onayla — Başlat</button>
        <button id="plan-edit"    class="btn btn-secondary">✏ Değiştir</button>
        <button id="plan-cancel"  class="btn btn-secondary">✕ İptal</button>
      </div>
    </div>`
  document.body.appendChild(overlay)

  document.getElementById('plan-approve').addEventListener('click', () => {
    overlay.remove()
    chat.addSystem('Plan onaylandı — başlatılıyor...')
    // Orijinal komutu "awaiting_approval: true" ile tekrar gönder
    agent.send({
      type:             'command',
      command:          _pendingCommand,
      awaiting_approval: true,
      project_id:       window.currentProjectId,
      style:            window.currentStyle || 'dark',
      files: { clips: media.clips, photos: media.photos, music: media.music, logo: media.logo }
    })
    _pendingCommand = null
  })

  document.getElementById('plan-edit').addEventListener('click', () => {
    overlay.remove()
    const input = document.getElementById('chat-input')
    if (input) { input.value = _pendingCommand || ''; input.focus() }
    _pendingCommand = null
  })

  document.getElementById('plan-cancel').addEventListener('click', () => {
    overlay.remove()
    chat.addSystem('İptal edildi.')
    _pendingCommand = null
  })
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;')
}

// ── Tema Toggle ───────────────────────────────────────────────────────────────
function toggleTheme() {
  const html  = document.documentElement
  const next  = (html.getAttribute('data-theme') || 'dark') === 'dark' ? 'light' : 'dark'
  html.setAttribute('data-theme', next)
  localStorage.setItem('theme', next)
  const btn = document.getElementById('theme-toggle')
  if (btn) btn.textContent = next === 'dark' ? '☀' : '🌙'
}

// ── Sihirbaz ──────────────────────────────────────────────────────────────────
function openWizard() {
  const wiz = new ProjectWizard(config => {
    window.currentProjectId = config.projectId
    window.currentStyle     = config.style
    Object.assign(media, { clips: config.clips, photos: config.photos,
                            music: config.music, logo: config.logo })
    renderMediaList()
    if (config.music) updateMusicInfo(config.music)
    if (config.logo)  updateLogoInfo(config.logo)
    updateToolbar()
    document.getElementById('btn-demo').disabled = !(media.clips.length || media.photos.length)
    showEditor()
    sendRender('demo')
  })
  wiz.setMedia(media.clips, media.photos, media.music, media.logo)
}

// ── WebSocket Bağlantısı ──────────────────────────────────────────────────────
class AgentConnection {
  constructor(url) { this.url = url; this.ws = null; this.reconnectDelay = 2000; this.handlers = {} }

  connect() {
    console.log('[ws] baglaniliyor:', this.url)
    try {
      this.ws = new WebSocket(this.url)
      this.ws.onopen    = () => {
        console.log('[ws] BAGLANDI!')
        setStatus(true)
        this.reconnectDelay = 2000
      }
      this.ws.onmessage = e  => { try { this._dispatch(JSON.parse(e.data)) } catch(err) { console.error('[ws parse]',err) } }
      this.ws.onclose   = (e) => {
        console.log('[ws] kapatildi, code:', e.code, 'reason:', e.reason)
        setStatus(false)
        setTimeout(() => this.connect(), this.reconnectDelay)
        this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 10000)
      }
      this.ws.onerror = e => console.error('[ws ERROR]', e.type, e)
    } catch(e) {
      console.error('[ws connect exception]', e)
      setTimeout(() => this.connect(), this.reconnectDelay)
    }
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) { this.ws.send(JSON.stringify(data)); return true }
    chat.addError('Agent bağlı değil — lütfen bekleyin')
    return false
  }

  on(type, fn)  { this.handlers[type] = fn }
  _dispatch(d)  {
    const h = this.handlers[d.type] || this.handlers['*']
    if (h) h(d); else console.log('[ws unhandled]', d.type)
  }
}

const agent = new AgentConnection(
  window.electronAPI?.agentWsUrl() || 'ws://localhost:8765/ws'
)

agent.on('plan', d => {
  showPlanApproval(d.text, d.command)
})

agent.on('progress', d => {
  setProgress(d)
  if (d.message) chat.addProgress(d.message)
})

agent.on('result', d => {
  resetProgress('Tamamlandı ✓')
  if (d.text)        chat.addAssistant(d.text)
  if (d.output_path) loadVideo(d.output_path)
  if (d.timeline)    renderTimeline(d.timeline)
  if (d.qa_score != null || d.qa_grade) {
    showQAResult(d.qa_score, d.qa_grade, d.qa_report)
    chat.addSystem(`QA: ${d.qa_grade || '?'} — ${d.qa_score != null ? Number(d.qa_score).toFixed(1) : '—'} / 100`)
  }
})

agent.on('error', d => {
  resetProgress('Hata')
  chat.addError(d.message || 'Bilinmeyen hata')
})

// ── DOMContentLoaded ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Tema
  const savedTheme = localStorage.getItem('theme') || 'dark'
  document.documentElement.setAttribute('data-theme', savedTheme)
  const themeBtn = document.getElementById('theme-toggle')
  if (themeBtn) themeBtn.textContent = savedTheme === 'dark' ? '☀' : '🌙'

  // ── Ana Ekran butonları
  document.getElementById('home-btn-new')?.addEventListener('click', () => {
    resetProjectState()   // Eski proje temizlenir
    showEditor()
    openWizard()
  })
  document.getElementById('home-btn-open')?.addEventListener('click', showProjectModal)

  // ── Toolbar butonları
  document.getElementById('tb-home-btn')?.addEventListener('click', showHome)
  document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme)
  document.getElementById('btn-save-project')?.addEventListener('click', saveProject)
  document.getElementById('btn-load-project')?.addEventListener('click', showProjectModal)
  document.getElementById('btn-wizard')?.addEventListener('click', openWizard)

  // ── Proje modal kapat
  document.getElementById('project-modal-close')?.addEventListener('click', () => {
    document.getElementById('project-modal').style.display = 'none'
  })
  document.getElementById('project-modal')?.addEventListener('click', e => {
    if (e.target.id === 'project-modal')
      document.getElementById('project-modal').style.display = 'none'
  })

  // ── Drag & Drop
  const setupDrop = (zoneId, handler) => {
    const z = document.getElementById(zoneId); if (!z) return
    z.addEventListener('dragover', e => { e.preventDefault(); z.classList.add('drag-over') })
    z.addEventListener('dragleave', () => z.classList.remove('drag-over'))
    z.addEventListener('drop', e => { e.preventDefault(); z.classList.remove('drag-over'); handler(e) })
  }
  setupDrop('drop-zone',  e => Array.from(e.dataTransfer.files).forEach(f => addFile(f.path)))
  setupDrop('music-zone', e => { const f = e.dataTransfer.files[0]; if (f) addFile(f.path) })
  setupDrop('logo-zone',  e => {
    const f = e.dataTransfer.files[0]
    if (f && /\.(png|jpg|svg)$/i.test(f.name)) { media.logo = f.path; updateLogoInfo(f.path) }
  })

  // ── Chat
  const sendBtn = document.getElementById('send-btn')
  const input   = document.getElementById('chat-input')
  sendBtn?.addEventListener('click', () => { sendCommand(input.value); input.value = '' })
  input?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendCommand(input.value); input.value = '' }
  })

  // ── Hızlı komutlar
  document.querySelectorAll('.quick-btn').forEach(b =>
    b.addEventListener('click', () => sendCommand(b.dataset.cmd)))

  // ── Render butonları
  document.getElementById('btn-demo')?.addEventListener('click',  () => sendRender('demo'))
  document.getElementById('btn-final')?.addEventListener('click', () => sendRender('final'))

  // ── Müzik URL indirme
  const musicUrlBtn = document.getElementById('music-url-btn')
  const musicUrlInp = document.getElementById('music-url-input')
  musicUrlBtn?.addEventListener('click', () => downloadMusicFromUrl(musicUrlInp?.value || ''))
  musicUrlInp?.addEventListener('keydown', e => {
    if (e.key === 'Enter') downloadMusicFromUrl(musicUrlInp.value)
  })

  // ── Chat temizle
  document.getElementById('btn-clear-chat')?.addEventListener('click', () => chat.clear())

  // ── QA detay toggle
  document.getElementById('qa-toggle-detail')?.addEventListener('click', () => {
    const d = document.getElementById('qa-detail')
    if (d) d.style.display = d.style.display === 'none' ? 'block' : 'none'
  })

  // ── Ctrl+S
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); saveProject() }
  })

  console.log('[app] DOMContentLoaded, baslaniyor...')
  // Başlangıçta ana ekranı göster + loading animasyonu
  showHome()
  updateToolbar()
  startLoadingAnimation()
  console.log('[app] agent.connect() cagriliyor, URL:', agent.url)
  agent.connect()
  console.log('[app] init tamamlandi')
})
