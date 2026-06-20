import path from "node:path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

// 端口固定:本项目前端永远 3310,后端 3320(strictPort=占用即报错,不自动漂移)
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: { port: 3310, strictPort: true },
  preview: { port: 3310, strictPort: true },
})
