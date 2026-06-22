import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// 端口固定 3311(与 scribe2 前端 3310 隔离),strictPort 占用即报错不漂移
export default defineConfig({
  plugins: [react()],
  server: { port: 3311, strictPort: true },
  preview: { port: 3311, strictPort: true },
})
