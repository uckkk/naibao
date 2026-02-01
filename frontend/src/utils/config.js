// API配置文件
export default {
  // Vite/uni-app 推荐：通过环境变量注入，避免在仓库里写死服务器地址
  // - 开发：frontend/.env.local（不提交）
  // - 示例：frontend/.env.example
  baseURL: (() => {
    const envBase = (typeof import.meta !== 'undefined' && import.meta.env)
      ? import.meta.env.VITE_API_BASE_URL
      : ''

    if (envBase) return String(envBase)

    // H5：默认用同源（推荐用 Nginx 反代 /api，避免跨域）
    if (typeof window !== 'undefined' && window.location && window.location.origin) {
      return String(window.location.origin)
    }

    // 其他平台：默认本机开发地址；生产请务必配置 VITE_API_BASE_URL
    return 'http://localhost:8080'
  })(),
  
  // 超时时间（毫秒）
  timeout: 10000,
}
