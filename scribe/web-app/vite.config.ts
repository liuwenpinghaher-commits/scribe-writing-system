import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 端口固定:本项目前端永远 3310,后端 3320(strictPort=占用即报错,不自动漂移)
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: { port: 3310, strictPort: true },
  preview: { port: 3310, strictPort: true },
})
