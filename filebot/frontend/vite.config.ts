import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5174,
    proxy: {
      // 认证相关API直接代理到FileBot后端（端口8001）
      '/api/v1/auth': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/v1\/auth/, '/api/v1/auth')
      },
      // 应用相关API直接代理到FileBot后端（端口8001）
      '/api/v1/apps': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/v1\/apps/, '/api/v1/apps')
      },
      // 文档相关API直接代理到FileBot后端（端口8001）
      '/api/v1/documents': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/v1\/documents/, '/api/v1/documents')
      },
      // 文件夹相关API直接代理到FileBot后端（端口8001）
      '/api/v1/folders': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/v1\/folders/, '/api/v1/folders')
      },
      // AI相关API直接代理到FileBot后端（端口8001）
      '/api/v1/ai': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/v1\/ai/, '/api/v1/ai')
      },
      // 搜索相关API直接代理到FileBot后端（端口8001）
      '/api/v1/search': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/v1\/search/, '/api/v1/search')
      },
      // 用户管理API直接代理到FileBot后端（端口8001）
      '/api/v1/users': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/v1\/users/, '/api/v1/users')
      },
      // 用户组管理API直接代理到FileBot后端（端口8001）
      '/api/v1/groups': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/v1\/groups/, '/api/v1/groups')
      },
      // 权限管理API直接代理到FileBot后端（端口8001）
      '/api/v1/permissions': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/v1\/permissions/, '/api/v1/permissions')
      },
      // Export 相关 API 代理到 FileBot 后端（端口8001）
      '/api/v1/import-to-webbot': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/api/v1/export': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
      },
      // Export-folder 专用代理（不做路径重写，webbot 后端直接用 /api/v1/export-folder）
      '/api/v1/export-folder': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      // 通用API代理规则（捕获其他 /api/v1/* 路径）
      '/api/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/v1/, '/content')
      },
      // FileBot文档静态文件（/content/dam）直连FileBot后端（端口8001）
      // 放在 /content 前面，优先级更高
      '/content/dam': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        // 不重写路径，FileBot后端直接处理 /content/dam/* 静态文件
      },
      // 内容相关请求也通过WebBot代理服务
      '/content': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        // 不重写路径，WebBot服务直接处理 /content/* 路由
      },
      // 代理GCWeb静态文件到WebBot代理（端口8000）
      '/gcweb': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        // 保留路径不变
      },
      // 代理设计文件到FileBot后端（端口8001），使预览如canada.ca般工作
      '/etc/designs': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        // 保留路径不变
      }
    }
  }
})
