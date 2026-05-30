// DaVinci Resolve Otomatik Baslatma + Durum Popup

const BASE = () => window.electronAPI?.agentHttpUrl() || 'http://localhost:8765'

async function checkDaVinciStatus() {
  try {
    const res  = await fetch(BASE() + '/davinci/status', { signal: AbortSignal.timeout(5000) })
    const data = await res.json()

    if (!data.bridge_active) {
      showDaVinciPopup(data)
    }
  } catch (e) {
    // Agent henuz hazir degil — atla
    console.log('[davinci] Durum kontrolu ertelendi:', e.message)
  }
}

function showDaVinciPopup(statusData) {
  if (document.getElementById('dvr-popup')) return

  const isRunning = statusData.resolve_running
  const consoleCmd = statusData.console_cmd || ''

  const overlay = document.createElement('div')
  overlay.id = 'dvr-popup'
  overlay.innerHTML = `
    <div id="dvr-popup-box">
      <div id="dvr-popup-icon">🎬</div>
      <h2 id="dvr-popup-title">DaVinci Resolve Hazir Degil</h2>
      <p id="dvr-popup-desc">
        ${isRunning
          ? 'DaVinci acik fakat Python koprusu kurulmamis.'
          : 'DaVinci Resolve kapali — renk grading icin gerekli.'}
      </p>

      <div id="dvr-status-bar">
        <div id="dvr-status-dot" class="dvr-dot-idle"></div>
        <span id="dvr-status-text">Hazir degil</span>
      </div>

      <div id="dvr-progress-wrap" style="display:none">
        <div id="dvr-progress-bar"></div>
        <span id="dvr-progress-label">Baslatiliyor...</span>
      </div>

      <div id="dvr-cmd-section">
        <p class="dvr-manual-label">Manuel baslatmak isterseniz DaVinci Console (Workspace → Console → Py3) a yapistirin:</p>
        <div id="dvr-cmd-wrap">
          <code id="dvr-cmd">${escapeHtml(consoleCmd)}</code>
          <button id="dvr-copy-btn" title="Komutu kopyala">📋</button>
        </div>
      </div>

      <div id="dvr-popup-footer">
        <button id="dvr-auto-btn" class="btn btn-primary">Otomatik Baslat</button>
        <button id="dvr-skip-btn" class="btn btn-secondary">Simdilik Atla</button>
      </div>
    </div>`

  document.body.appendChild(overlay)

  // Kopyala
  document.getElementById('dvr-copy-btn').addEventListener('click', () => {
    navigator.clipboard.writeText(consoleCmd).then(() => {
      const btn = document.getElementById('dvr-copy-btn')
      btn.textContent = '✓'
      setTimeout(() => { btn.textContent = '📋' }, 1500)
    })
  })

  // Otomatik Baslat
  document.getElementById('dvr-auto-btn').addEventListener('click', () => startAutoLaunch())

  // Atla
  document.getElementById('dvr-skip-btn').addEventListener('click', () => {
    overlay.remove()
    if (typeof chat !== 'undefined')
      chat.addSystem('DaVinci Resolve atlandi — renk grading ozellikleri kullanilamaz')
  })

  // Otomatik baslat — 1 saniye sonra otomatik tetikle
  setTimeout(() => startAutoLaunch(), 1000)
}

async function startAutoLaunch() {
  const autoBtn   = document.getElementById('dvr-auto-btn')
  const skipBtn   = document.getElementById('dvr-skip-btn')
  const statusDot = document.getElementById('dvr-status-dot')
  const statusTxt = document.getElementById('dvr-status-text')
  const progWrap  = document.getElementById('dvr-progress-wrap')
  const progBar   = document.getElementById('dvr-progress-bar')
  const progLabel = document.getElementById('dvr-progress-label')

  if (!autoBtn) return

  autoBtn.disabled = true
  autoBtn.textContent = 'Baslatiliyor...'
  if (progWrap) progWrap.style.display = 'block'
  if (statusDot) statusDot.className = 'dvr-dot-loading'

  // Ilerleme animasyonu (tahmini 30sn)
  const steps = [
    { pct:  5, label: 'DaVinci Resolve baslatiliyor...' },
    { pct: 25, label: 'Pencere yukleniyor...' },
    { pct: 50, label: 'Console aciliyor...' },
    { pct: 70, label: 'Bridge script inject ediliyor...' },
    { pct: 88, label: 'Baglanti bekleniyor...' },
  ]

  let stepIdx = 0
  const stepTimer = setInterval(() => {
    if (stepIdx < steps.length) {
      const s = steps[stepIdx++]
      if (progBar)   progBar.style.width  = s.pct + '%'
      if (progLabel) progLabel.textContent = s.label
      if (statusTxt) statusTxt.textContent = s.label
    }
  }, 5000)

  try {
    const res  = await fetch(BASE() + '/davinci/autostart', {
      method: 'POST',
      signal: AbortSignal.timeout(60000)   // 60sn max
    })
    const data = await res.json()

    clearInterval(stepTimer)

    if (data.ok) {
      // Basarili
      if (progBar)   progBar.style.width  = '100%'
      if (progLabel) progLabel.textContent = 'Baglanti kuruldu!'
      if (statusDot) statusDot.className   = 'dvr-dot-ok'
      if (statusTxt) statusTxt.textContent = 'Bridge hazir'
      if (typeof chat !== 'undefined')
        chat.addSystem('DaVinci Resolve baglandi ve hazir')
      setTimeout(() => document.getElementById('dvr-popup')?.remove(), 1500)
    } else {
      // Basarisiz — manuel moda gec
      clearInterval(stepTimer)
      if (progBar)   progBar.style.width  = '0%'
      if (progLabel) progLabel.textContent = 'Otomatik baslatma basarisiz'
      if (statusDot) statusDot.className   = 'dvr-dot-idle'
      if (statusTxt) statusTxt.textContent = data.message || 'Hata'
      if (autoBtn) { autoBtn.disabled = false; autoBtn.textContent = 'Tekrar Dene' }
    }
  } catch (e) {
    clearInterval(stepTimer)
    if (statusDot) statusDot.className   = 'dvr-dot-idle'
    if (statusTxt) statusTxt.textContent = 'Baglanti hatasi: ' + e.message
    if (autoBtn) { autoBtn.disabled = false; autoBtn.textContent = 'Tekrar Dene' }
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

// Agent baglantisi kurulduktan 3sn sonra kontrol et
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(checkDaVinciStatus, 3000)
})
