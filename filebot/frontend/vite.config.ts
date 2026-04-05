import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
      },
      '/content': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => {
          // 将 /content/* 映射到 /api/v1/documents/by-path/content/*
          // 例如: /content/dam/... → /api/v1/documents/by-path/content/dam/...
          // path 是 /dam/...（因为匹配了 /content 前缀）
          return '/api/v1/documents/by-path/content' + path;
        }
      }
    }
  }
})
