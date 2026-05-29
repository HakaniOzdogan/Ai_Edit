# PHASE 6 — Arayüz (UI)

Önceki adım: PHASE_5_ELECTRON.md
Sonraki adım: PHASE_7_DAVINCI.md

---

## Amaç

Proje kurulum sihirbazı, medya paneli, preview ekranı, chat paneli ve timeline'ı uygula.
TRD'deki frontend tasarımını gerçek Electron renderer koduna dönüştür.

---

## 6.1 — Layout CSS

`electron/renderer/styles.css` — 3 sütun grid layout:

```css
* { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg-primary:   #0d0d0f;
  --bg-secondary: #111114;
  --bg-tertiary:  #1a1a22;
  --border:       #2a2a2e;
  --accent:       #a78bfa;
  --accent-green: #4ade80;
  --text-primary: #dddddd;
  --text-muted:   #666666;
  --text-dim:     #444444;
}

body { background: var(--bg-primary); color: var(--text-primary);
       font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       height: 100vh; overflow: hidden; }

#app { display: grid;
       grid-template-rows: 44px 1fr 160px;
       grid-template-columns: 260px 1fr 300px;
       height: 100vh; }

#titlebar { grid-column: 1 / -1; background: var(--bg-secondary);
            border-bottom: 0.5px solid var(--border);
            display: flex; align-items: center; padding: 0 16px; gap: 10px;
            -webkit-app-region: drag; }

#left-panel  { background: var(--bg-secondary); border-right:  0.5px solid var(--border); overflow: hidden; display: flex; flex-direction: column; }
#center-panel{ display: flex; flex-direction: column; overflow: hidden; }
#right-panel { background: var(--bg-secondary); border-left: 0.5px solid var(--border); display: flex; flex-direction: column; overflow: hidden; }
#timeline-panel { grid-column: 1 / -1; background: #0a0a0d; border-top: 0.5px solid var(--border); }

.status-dot { width: 8px; height: 8px; border-radius: 50%; margin-left: auto; }
.status-dot.connected    { background: var(--accent-green); }
.status-dot.disconnected { background: #ef4444; }
```

---

## 6.2 — Proje Kurulum Sihirbazı

Medya yüklendikten sonra otomatik açılır.
`electron/renderer/wizard.js` — 5 adımlı sihirbaz (PHASE_6 UI tasarımındaki etkileşimli sihirbazın Electron implementasyonu).

Sihirbaz tamamlandığında şu veriyi agent'a gönder:

```javascript
function startProject(config) {
  agent.send({
    type: 'command',
    command: `Proje kurgusunu başlat. Tarz: ${config.style}. Müzik: ${config.music}. Referans: ${config.reference || 'yok'}.`,
    project_id: config.projectId,
    style: config.style,
    files: {
      clips:  config.clips,
      photos: config.photos,
      music:  config.music,
      logo:   config.logo
    },
    profile: config.reference === 'profile' ? config.selectedProfile : null
  })
}
```

---

## 6.3 — Chat Panel

```javascript
class ChatPanel {
  constructor(containerId, agentConnection) {
    this.container = document.getElementById(containerId)
    this.agent = agentConnection
    this._setupHandlers()
  }

  _setupHandlers() {
    this.agent.on('progress', d => this._addProgress(d))
    this.agent.on('result',   d => this._addResult(d))
    this.agent.on('error',    d => this._addError(d))
  }

  sendCommand(text) {
    this._addUserMessage(text)
    return this.agent.send({
      type: 'command',
      command: text,
      project_id: window.currentProjectId || 'default'
    })
  }

  _addUserMessage(text) { /* Kullanıcı balonu ekle */ }
  _addProgress(data)    { /* "X çalışıyor..." satırı ekle */ }
  _addResult(data)      { /* AI yanıt balonu ekle */ }
  _addError(data)       { /* Kırmızı hata mesajı ekle */ }
}
```

---

## Doğrulama Kontrolleri

```bash
npm start
# Kontroller:
# - Sihirbaz ilk açılışta görünüyor
# - Seçim yapmadan Devam butonu kilitli
# - Chat panelinde mesaj gönderilebiliyor
# - Agent'a mesaj gidip progress geliyor
# - Timeline panel görünüyor
```

---

## Geçiş Kriteri

- Sihirbaz 5 adım tamamlanabiliyor
- Chat'ten komut gönderilebiliyor
- Agent progress mesajları chat'te görünüyor
- Layout 3 sütun doğru render oluyor

Geçildiyse PHASE_7_DAVINCI.md'ye geç.
