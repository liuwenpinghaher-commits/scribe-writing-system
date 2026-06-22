import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
// host 127.0.0.1 修上次 IPv6([::1])导致 127.0.0.1 连不上的问题;端口 3311 strictPort
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { host: '127.0.0.1', port: 3311, strictPort: true },
  preview: { host: '127.0.0.1', port: 3311, strictPort: true },
})
