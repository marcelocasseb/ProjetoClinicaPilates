import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Identificador desta build: vai embutido no JS (__APP_VERSION__) e publicado em
// /version.json. A aba aberta compara os dois para saber que saiu versão nova
// (ver src/components/AvisoVersao.jsx).
const APP_VERSION = new Date().toISOString()

function versionJson() {
  return {
    name: 'version-json',
    apply: 'build',
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'version.json',
        source: JSON.stringify({ version: APP_VERSION }),
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), versionJson()],
  define: {
    __APP_VERSION__: JSON.stringify(APP_VERSION),
  },
})
