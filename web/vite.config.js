import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5123,
    host: '0.0.0.0',
    proxy: {
      // 开发期把 /api/* 反代到后端容器，浏览器视角下是同源，规避 CORS
      '/api': {
        // 前端在本机跑（pnpm dev），后端 API 在 Docker 内监听 5050，
        // 通过 docker-compose 映射到宿主机 5151。
        target: process.env.VITE_API_URL || 'http://localhost:5151',
        changeOrigin: true
      }
    }
  }
})
