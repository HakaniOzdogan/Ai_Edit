const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getAppPath:      ()     => ipcRenderer.invoke('get-app-path'),
  getVersion:      ()     => ipcRenderer.invoke('get-version'),
  isPackaged:      ()     => ipcRenderer.invoke('is-packaged'),
  agentWsUrl:      ()     => 'ws://localhost:8765/ws',
  agentHttpUrl:    ()     => 'http://localhost:8765',
  platform:        ()     => process.platform,
  openFileDialog:  (opts) => ipcRenderer.invoke('open-file-dialog', opts),
  onAgentCrashed:  (cb)   => ipcRenderer.on('agent-crashed', (_, data) => cb(data)),
})
