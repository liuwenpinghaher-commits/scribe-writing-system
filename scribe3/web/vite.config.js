import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1', port: 3311, strictPort: true,
    // 同源代理:前端请求 /api/* → vite 后台转发到后端 :3321(去掉 /api 前缀)。
    // 消除跨端口/跨源 POST——浏览器扩展/安全策略常拦跨端口 POST,同源后浏览器眼里全是本源请求。
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:3321',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        // 选择环 run_selection 同步跑 2-5 分钟(三路真机生成),proxy 默认超时会中途掐断长请求。
        // 拉到 600s 匹配后端 LLM 超时,长请求不被 proxy 提前中断。
        timeout: 600000,
        proxyTimeout: 600000,
      },
    },
  },
  preview: { host: '127.0.0.1', port: 3311, strictPort: true },
  test: {
    environment: 'jsdom',
    globals: true,
    environmentOptions: { jsdom: { url: 'http://localhost' } },
    setupFiles: ['./src/lib/vitest.setup.js'],
    // e2e/*.mjs 是 Playwright/脚本旅程,不是 vitest suite;纳入会「No test suite found」。
    exclude: ['**/node_modules/**', '**/dist/**', 'e2e/**'],
  },
})
