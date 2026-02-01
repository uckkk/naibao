import { defineConfig, loadEnv } from 'vite'
// @ts-ignore
// 使用require方式导入（CommonJS）
import { createRequire } from 'module'
import { fileURLToPath } from 'url'
import path from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// 设置 Uni-app 环境变量
// 统一指定源码目录（该仓库的 pages.json/manifest.json/main.* 都在 src 下）。
// 注意：uni CLI 可能会默认把 UNI_INPUT_DIR 指到项目根目录，导致 h5 运行时无法注入 __uniConfig/__uniRoutes 等关键变量。
process.env.UNI_INPUT_DIR = path.resolve(__dirname, 'src')
if (!process.env.UNI_PLATFORM) {
  process.env.UNI_PLATFORM = 'h5'
}
if (!process.env.VITE_ROOT_DIR) {
  process.env.VITE_ROOT_DIR = __dirname
}

const require = createRequire(import.meta.url)
const uniPlugin = require('@dcloudio/vite-plugin-uni')

// uniPlugin.default 是函数
const uni = uniPlugin.default

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '')
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8080'
  const isH5 = process.env.UNI_PLATFORM === 'h5'

  return {
    plugins: [
      uni()
    ],
    root: __dirname,
    server: {
      host: '0.0.0.0',
      port: 5173,
      open: false,
      // H5 开发时：让手机只访问前端同源地址（5173），由 Vite 反代 /api 到后端（8080）
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
        },
        '/ws': {
          target: apiProxyTarget,
          ws: true,
          changeOrigin: true,
        }
      }
    },
    css: {
      postcss: {
        plugins: [
          // Uni-app会自动处理rpx转换
        ]
      }
    },
    // 确保正确解析
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
        // uni-h5 运行时依赖的 Vue API（如 injectHook）来自 @dcloudio 的定制 Vue 包。
        ...(isH5 ? { vue: '@dcloudio/uni-h5-vue' } : {})
      }
    },
    // 优化依赖预构建
    optimizeDeps: {
      exclude: ['vue']
    }
  }
})
