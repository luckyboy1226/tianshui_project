import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [vue()],
    define: {
      global: 'globalThis',
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        buffer: 'buffer'
      }
    },
    optimizeDeps: {
      include: ['buffer']
    },
    server: {
      port: 3000,
      strictPort: true,
      proxy: {
        // 开发环境默认代理到本机 Django；需要改端口时可配置 VITE_PROXY_TARGET
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
        },
        '/media': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
        }
      }
    },
    build: {
      chunkSizeWarningLimit: 1000,
      rollupOptions: {
        onwarn(warning, warn) {
          if (warning.code === 'INVALID_ANNOTATION' && warning.id?.includes('@vueuse/core')) {
            return
          }
          warn(warning)
        },
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) {
              return
            }
            if (id.includes('/ol/')) {
              return 'vendor-ol'
            }
            if (id.includes('/element-plus/') || id.includes('/@element-plus/')) {
              return 'vendor-element-plus'
            }
            if (id.includes('/vue') || id.includes('/@vue/')) {
              return 'vendor-vue'
            }
            if (id.includes('/axios/')) {
              return 'vendor-axios'
            }
            if (id.includes('/echarts/')) {
              return 'vendor-echarts'
            }
            if (
              id.includes('/shpjs/') ||
              id.includes('/jszip/') ||
              id.includes('/pbf/') ||
              id.includes('/proj4/') ||
              id.includes('/@mapbox/')
            ) {
              return 'vendor-geo'
            }
            return 'vendor'
          }
        }
      }
    }
  }
})
