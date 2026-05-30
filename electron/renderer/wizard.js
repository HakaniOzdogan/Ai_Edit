// ── Proje Kurulum Sihirbazı ───────────────────────────────────────────────────

class ProjectWizard {
  constructor(onComplete) {
    this.step = 1
    this.total = 5
    this.onComplete = onComplete
    this.config = {
      projectId: 'proj_' + Date.now(),
      type: null, style: null, music: null,
      reference: null, selectedProfile: null,
      clips: [], photos: [], logo: null
    }
    this._buildUI()
  }

  _buildUI() {
    this.overlay = document.createElement('div')
    this.overlay.id = 'wizard-overlay'
    this.overlay.innerHTML = `
      <div id="wizard-box">
        <div id="wizard-header">
          <span id="wizard-title">Yeni Proje</span>
          <div id="wizard-steps-indicator"></div>
        </div>
        <div id="wizard-progress-bar"><div id="wizard-progress-fill"></div></div>
        <div id="wizard-body"></div>
        <div id="wizard-error"></div>
        <div id="wizard-footer">
          <button id="wizard-back" class="btn btn-secondary">Geri</button>
          <button id="wizard-next" class="btn btn-primary">Devam</button>
        </div>
      </div>`
    document.body.appendChild(this.overlay)

    document.getElementById('wizard-next').addEventListener('click', () => this.next())
    document.getElementById('wizard-back').addEventListener('click', () => this.back())
    this._render()
  }

  _render() {
    const body = document.getElementById('wizard-body')
    const fill = document.getElementById('wizard-progress-fill')
    const title = document.getElementById('wizard-title')
    const indicator = document.getElementById('wizard-steps-indicator')
    const backBtn = document.getElementById('wizard-back')
    const nextBtn = document.getElementById('wizard-next')

    fill.style.width = ((this.step / this.total) * 100) + '%'
    backBtn.style.display = this.step === 1 ? 'none' : 'inline-block'
    nextBtn.textContent = this.step === this.total ? 'Başlat' : 'Devam'

    indicator.textContent = `${this.step} / ${this.total}`
    document.getElementById('wizard-error').textContent = ''

    const steps = [
      { title: 'Proje Tipi', content: this._step1() },
      { title: 'Edit Tarzı', content: this._step2() },
      { title: 'Müzik', content: this._step3() },
      { title: 'Referans', content: this._step4() },
      { title: 'Özet', content: this._step5() },
    ]
    const s = steps[this.step - 1]
    title.textContent = s.title
    body.innerHTML = ''
    body.appendChild(s.content)
  }

  _step1() {
    const types = [
      { id: 'product', label: 'Ürün Reklamı', icon: '📦' },
      { id: 'event',   label: 'Etkinlik',      icon: '🎉' },
      { id: 'social',  label: 'Sosyal Medya',  icon: '📱' },
      { id: 'travel',  label: 'Seyahat',       icon: '✈️' },
    ]
    return this._choiceGrid(types, 'type', this.config.type)
  }

  _step2() {
    const styles = [
      { id: 'dark', label: 'Dark Cinematic', icon: '🎬' },
      { id: 'fast', label: 'Fast Cut',       icon: '⚡' },
      { id: 'warm', label: 'Warm Lifestyle', icon: '☀️' },
      { id: 'corp', label: 'Corporate',      icon: '💼' },
    ]
    return this._choiceGrid(styles, 'style', this.config.style)
  }

  _step3() {
    const div = document.createElement('div')
    div.className = 'wizard-step-content'
    div.innerHTML = `
      <div class="wizard-music-zone ${this.config.music ? 'has-file' : ''}" id="wiz-music-drop">
        <div class="wiz-music-icon">🎵</div>
        <p>${this.config.music ? this.config.music.split(/[\\/]/).pop() : 'Müzik dosyasını buraya sürükle'}</p>
        <p class="wiz-hint">MP3, WAV, AAC, FLAC</p>
      </div>
      <div class="wiz-or">— veya —</div>
      <button class="btn btn-secondary" id="wiz-skip-music">Sonraya Bırak</button>`

    setTimeout(() => {
      const zone = document.getElementById('wiz-music-drop')
      if (zone) {
        zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over') })
        zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'))
        zone.addEventListener('drop', e => {
          e.preventDefault()
          zone.classList.remove('drag-over')
          const f = e.dataTransfer.files[0]
          if (f && /\.(mp3|wav|aac|flac)$/i.test(f.name)) {
            this.config.music = f.path
            this._render()
          }
        })
      }
      document.getElementById('wiz-skip-music')?.addEventListener('click', () => {
        this.config.music = null
        this.next(true)
      })
    }, 0)
    return div
  }

  _step4() {
    const div = document.createElement('div')
    div.className = 'wizard-step-content'
    div.innerHTML = `
      <p class="wiz-subtitle">Referans video veya marka profili (isteğe bağlı)</p>
      <div class="wiz-ref-options">
        <div class="wiz-ref-card ${this.config.reference === 'none' ? 'selected' : ''}" data-ref="none">
          <span>⏭</span><p>Referanssız Devam</p>
        </div>
        <div class="wiz-ref-card ${this.config.reference === 'link' ? 'selected' : ''}" data-ref="link">
          <span>🔗</span><p>Referans Link</p>
        </div>
        <div class="wiz-ref-card ${this.config.reference === 'profile' ? 'selected' : ''}" data-ref="profile">
          <span>🎨</span><p>Kayıtlı Profil</p>
        </div>
      </div>
      <div id="wiz-ref-link-wrap" style="display:none;margin-top:10px">
        <input id="wiz-ref-url" type="text" placeholder="https://... veya lokal dosya yolu"
               style="width:100%;padding:7px 10px;background:var(--bg-tertiary);border:0.5px solid var(--border);border-radius:6px;color:var(--text-primary);font-size:12px;outline:none">
      </div>
      <div id="wiz-ref-profile-wrap" style="display:none;margin-top:10px">
        <select id="wiz-profile-select" style="width:100%;padding:7px 10px;background:var(--bg-tertiary);border:0.5px solid var(--border);border-radius:6px;color:var(--text-primary);font-size:12px">
          <option value="">Yükleniyor...</option>
        </select>
      </div>`
    setTimeout(() => {
      div.querySelectorAll('.wiz-ref-card').forEach(card => {
        card.addEventListener('click', () => {
          this.config.reference = card.dataset.ref
          div.querySelectorAll('.wiz-ref-card').forEach(c => c.classList.remove('selected'))
          card.classList.add('selected')
          // Koşullu input göster
          document.getElementById('wiz-ref-link-wrap').style.display =
            this.config.reference === 'link' ? 'block' : 'none'
          const profileWrap = document.getElementById('wiz-ref-profile-wrap')
          profileWrap.style.display = this.config.reference === 'profile' ? 'block' : 'none'
          // Profil listesini yükle
          if (this.config.reference === 'profile') this._loadProfiles()
        })
      })
      document.getElementById('wiz-ref-url')?.addEventListener('input', e => {
        this.config.referenceUrl = e.target.value.trim()
      })
      document.getElementById('wiz-profile-select')?.addEventListener('change', e => {
        this.config.selectedProfile = e.target.value
      })
    }, 0)
    return div
  }

  async _loadProfiles() {
    const sel = document.getElementById('wiz-profile-select')
    if (!sel) return
    try {
      const base = window.electronAPI?.agentHttpUrl() || 'http://localhost:8765'
      const res  = await fetch(base + '/profiles')
      const data = await res.json()
      if (data.profiles?.length) {
        sel.innerHTML = data.profiles
          .map(p => `<option value="${p}">${p}</option>`)
          .join('')
        this.config.selectedProfile = data.profiles[0]
      } else {
        sel.innerHTML = '<option value="">Kayıtlı profil yok</option>'
      }
    } catch {
      sel.innerHTML = '<option value="">Profiller yüklenemedi</option>'
    }
  }

  _step5() {
    const div = document.createElement('div')
    div.className = 'wizard-step-content wizard-summary'
    const styleLabels = { dark: 'Dark Cinematic', fast: 'Fast Cut', warm: 'Warm Lifestyle', corp: 'Corporate' }
    const typeLabels  = { product: 'Ürün Reklamı', event: 'Etkinlik', social: 'Sosyal Medya', travel: 'Seyahat' }
    div.innerHTML = `
      <div class="summary-row"><span>Proje Tipi</span><strong>${typeLabels[this.config.type] || '—'}</strong></div>
      <div class="summary-row"><span>Edit Tarzı</span><strong>${styleLabels[this.config.style] || '—'}</strong></div>
      <div class="summary-row"><span>Müzik</span><strong>${this.config.music ? this.config.music.split(/[\\/]/).pop() : 'Seçilmedi'}</strong></div>
      <div class="summary-row"><span>Video</span><strong>${this.config.clips.length} klip</strong></div>
      <div class="summary-row"><span>Fotoğraf</span><strong>${this.config.photos.length} dosya</strong></div>`
    return div
  }

  _choiceGrid(items, field, current) {
    const div = document.createElement('div')
    div.className = 'wizard-choice-grid'
    items.forEach(item => {
      const card = document.createElement('div')
      card.className = 'wizard-choice-card' + (current === item.id ? ' selected' : '')
      card.innerHTML = `<span class="choice-icon">${item.icon}</span><p>${item.label}</p>`
      card.addEventListener('click', () => {
        this.config[field] = item.id
        div.querySelectorAll('.wizard-choice-card').forEach(c => c.classList.remove('selected'))
        card.classList.add('selected')
      })
      div.appendChild(card)
    })
    return div
  }

  _validate() {
    const required = { 1: 'type', 2: 'style' }
    const field = required[this.step]
    if (field && !this.config[field]) {
      document.getElementById('wizard-error').textContent = 'Lütfen bir seçim yapın.'
      return false
    }
    // Step 3: müzik opsiyonel ama uyarı ver
    if (this.step === 3 && !this.config.music) {
      document.getElementById('wizard-error').textContent =
        '⚠ Müzik seçilmedi — beat senkronizasyonu yapılamaz, devam etmek için tekrar tıkla'
      // İlk tıklamada uyar ama blokla, ikinci tıklamada geç
      if (!this._musicWarningShown) {
        this._musicWarningShown = true
        return false
      }
      this._musicWarningShown = false
    }
    return true
  }

  next(force = false) {
    if (!force && !this._validate()) return
    if (this.step === this.total) { this._finish(); return }
    this.step++
    this._render()
  }

  back() {
    if (this.step > 1) { this.step--; this._render() }
  }

  setMedia(clips, photos, music, logo) {
    this.config.clips  = clips
    this.config.photos = photos
    if (music) this.config.music = music
    if (logo)  this.config.logo  = logo
  }

  _finish() {
    this.overlay.remove()
    const now = new Date()
    this.onComplete({
      ...this.config,
      name:         `Proje ${now.toLocaleDateString('tr')} ${now.toLocaleTimeString('tr', {hour:'2-digit',minute:'2-digit'})}`,
      music_choice: this.config.music ? 'file' : 'none',
    })
  }

  destroy() {
    this.overlay?.remove()
  }
}
