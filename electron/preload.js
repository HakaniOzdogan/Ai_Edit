const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getAppPath:   ()  => ipcRenderer.invoke('get-app-path'),
  agentWsUrl:   ()  => 'ws://localhost:8765/ws',
  agentHttpUrl: ()  => 'http://localhost:8765',
  platform:     ()  => process.platform,
})
