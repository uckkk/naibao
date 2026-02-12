// API请求封装（统一：支持 GET query、H5 优先 fetch、其他平台回退 uni.request）
import config from './config.js'

const API_PREFIX = '/api'
const rawBaseURL = String(config?.baseURL || '').replace(/\/+$/, '')
const BASE_URL = rawBaseURL.endsWith(API_PREFIX) ? rawBaseURL : rawBaseURL + API_PREFIX
const REQUEST_TIMEOUT = config?.timeout || 30000
const isDev = typeof process !== 'undefined'
  ? process.env?.NODE_ENV !== 'production'
  : false

// 约定：401（需要重新登录）时，API 层会发起跳转。
// 为避免各页面重复 toast（“像页面集合”），用一个哨兵 title 抑制无意义的错误提示。
export const NB_AUTH_REDIRECT_TOAST_TITLE = '__NB_AUTH_REDIRECT__'
const NB_AUTH_NOTICE_KEY = 'nb_auth_notice'

let authRedirecting = false
let authRedirectAtMs = 0

function isPublicApiPath(path) {
  return typeof path === 'string' && path.startsWith('/public/')
}

function isOnLoginPage() {
  try {
    if (typeof location !== 'undefined' && String(location.hash || '').includes('/pages/login/index')) {
      return true
    }
    if (typeof getCurrentPages === 'function') {
      const pages = getCurrentPages() || []
      const last = pages[pages.length - 1]
      const route = (last && (last.route || last.$page?.route)) || ''
      return typeof route === 'string' && route.includes('pages/login/index')
    }
  } catch {}
  return false
}

function setAuthNotice(message) {
  if (!message) return
  try {
    const existing = uni.getStorageSync(NB_AUTH_NOTICE_KEY)
    if (existing) {
      const cur = String(existing)
      const next = String(message)
      if (cur === next) return
      const curExpired = cur.includes('过期')
      const nextExpired = next.includes('过期')
      // 已经有“过期”提示时，不要被“请先登录”覆盖
      if (curExpired && !nextExpired) return
      // 只有更强的“过期”提示才允许覆盖
      if (!nextExpired) return
    }
    uni.setStorageSync(NB_AUTH_NOTICE_KEY, String(message))
  } catch {}
}

function handleAuthExpired(reason) {
  const now = Date.now()
  if (authRedirecting && now - authRedirectAtMs < 1500) return
  authRedirecting = true
  authRedirectAtMs = now

  try {
    uni.removeStorageSync('token')
    uni.removeStorageSync('user')
    uni.removeStorageSync('currentBaby')
  } catch {}

  // 让登录页知道“为何回到这里”（一次性提示）
  const msg = reason === 'expired'
    ? '登录已过期，请重新登录'
    : '请先登录'
  setAuthNotice(msg)

  // 避免在登录页再次触发 reLaunch 导致闪烁/循环
  if (!isOnLoginPage()) {
    try {
      uni.reLaunch({ url: '/pages/login/index' })
    } catch {}
  }

  setTimeout(() => {
    authRedirecting = false
  }, 2000)
}

function toQueryString(data) {
  if (!data || typeof data !== 'object') return ''
  const pairs = []
  for (const [key, value] of Object.entries(data)) {
    if (value === undefined || value === null || value === '') continue
    pairs.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
  }
  return pairs.length ? pairs.join('&') : ''
}

function sanitizeLogData(data) {
  if (!data || typeof data !== 'object') return data
  const masked = new Set(['password', 'old_password', 'new_password'])
  const out = Array.isArray(data) ? [...data] : { ...data }
  for (const k of Object.keys(out)) {
    if (masked.has(k)) out[k] = '***'
  }
  return out
}

function buildUrl(baseURL, path, method, data) {
  const upper = String(method || 'GET').toUpperCase()
  let url = baseURL + path
  if (upper === 'GET' || upper === 'DELETE') {
    const qs = toQueryString(data)
    if (qs) url += (url.includes('?') ? '&' : '?') + qs
  }
  return url
}

class ApiClient {
  constructor() {
    this.baseURL = BASE_URL
  }
  
  request(options) {
    return new Promise((resolve, reject) => {
      const token = uni.getStorageSync('token')
      const method = options.method || 'GET'
      const data = options.data || {}
      const fullUrl = buildUrl(this.baseURL, options.url, method, data)
      const isPublic = isPublicApiPath(options.url)
      const silent = !!options.silent

      if (isDev && !silent) {
        // 控制台噪音会显著增加排障成本，这里仅在开发态打印关键字段
        console.log(`[API] ${method} ${fullUrl}`, sanitizeLogData(data))
      }
      
      // 强制优先使用fetch API（更好的CORS支持）
      const useFetch = typeof fetch !== 'undefined' || (typeof window !== 'undefined' && typeof window.fetch !== 'undefined')
      
      if (useFetch) {
        const fetchFn = typeof fetch !== 'undefined' ? fetch : window.fetch
        const fetchOptions = {
          method,
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            ...options.header
          },
          mode: 'cors',
          cache: 'no-cache'
        }
        
        if (String(method).toUpperCase() !== 'GET') {
          fetchOptions.body = JSON.stringify(data || {})
        }
        
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT)
        
        fetchFn(fullUrl, { ...fetchOptions, signal: controller.signal })
          .then(async (response) => {
            clearTimeout(timeoutId)
            let resBody = null
            try {
              resBody = await response.json()
            } catch {
              // 非 JSON 响应（或空 body），保持为 null
            }
            
	            if (response.ok) {
	              resolve(resBody ?? {})
	            } else if (response.status === 401) {
                if (isPublic) {
                  const errorMsg = resBody?.error || resBody?.message || `请求失败 (${response.status})`
                  reject(new Error(errorMsg))
                  return
                }
	              handleAuthExpired(token ? 'expired' : 'required')
                const err = new Error(NB_AUTH_REDIRECT_TOAST_TITLE)
                err.code = 'AUTH_EXPIRED'
	              reject(err)
	            } else {
	              const errorMsg = resBody?.error || resBody?.message || `请求失败 (${response.status})`
	              if (!silent) {
                  const log = response.status >= 500 ? console.error : console.warn
                  log(`[API ${response.status}] ${fullUrl}`, errorMsg)
                }
                const err = new Error(errorMsg)
                err.status = response.status
                err.url = fullUrl
	              reject(err)
            }
          })
          .catch((error) => {
            clearTimeout(timeoutId)
            
            let errorMsg = '网络错误，请检查网络连接'
            if (error.name === 'AbortError') {
              errorMsg = '请求超时，请检查网络连接或服务器状态'
            } else if (error.message) {
              errorMsg = error.message
            }
            
            // fetch失败，回退到uni.request
            this.requestWithUni(options, resolve, reject, token, fullUrl)
          })
        return
      }
      
      // fetch不可用，使用uni.request
      this.requestWithUni(options, resolve, reject, token, fullUrl)
    })
  }
  
  requestWithUni(options, resolve, reject, token, fullUrl) {
    const method = options.method || 'GET'
    const upper = String(method).toUpperCase()
    const isPublic = isPublicApiPath(options.url)
    const silent = !!options.silent
    uni.request({
      url: fullUrl,
      method: upper,
      // GET/DELETE 的 query 已经拼到 URL，避免重复追加
      data: (upper === 'GET' || upper === 'DELETE') ? {} : (options.data || {}),
      header: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
        ...options.header
      },
      timeout: REQUEST_TIMEOUT,
      success: (res) => {
        if (isDev) console.log(`[API] ${res.statusCode} ${fullUrl}`, res.data)
        
	        if (res.statusCode === 200) {
	          resolve(res.data)
	        } else if (res.statusCode === 401) {
            if (isPublic) {
              const errorMsg = res.data?.error || res.data?.message || `请求失败 (${res.statusCode})`
              reject(new Error(errorMsg))
              return
            }
	          // Token过期/未登录，跳转登录（提示收敛到登录页）
	          handleAuthExpired(token ? 'expired' : 'required')
            const err = new Error(NB_AUTH_REDIRECT_TOAST_TITLE)
            err.code = 'AUTH_EXPIRED'
	          reject(err)
	        } else {
	          const errorMsg = res.data?.error || res.data?.message || `请求失败 (${res.statusCode})`
            if (!silent) {
              const log = res.statusCode >= 500 ? console.error : console.warn
              log(`[API ${res.statusCode}] ${fullUrl}`, errorMsg)
            }
            const err = new Error(errorMsg)
            err.status = res.statusCode
            err.url = fullUrl
	          reject(err)
        }
      },
      fail: (err) => {
        // 处理各种错误情况
        if (!silent) console.error(`[API失败] ${fullUrl}`, err)
        
        let errorMsg = '网络错误，请检查网络连接'
        
        if (err.errMsg) {
          if (err.errMsg.includes('timeout')) {
            errorMsg = '请求超时，请检查网络连接或服务器状态'
          } else if (err.errMsg.includes('fail')) {
            if (err.errMsg.includes('network')) {
              errorMsg = '网络连接失败，请检查网络设置'
            } else {
              errorMsg = '请求失败，请检查服务器是否正常运行'
            }
          }
        }
        
        reject(new Error(errorMsg))
      }
    })
  }
  
  get(url, data) {
    const opts = arguments.length >= 3 ? arguments[2] : null
    return this.request({ url, method: 'GET', data, ...(opts && typeof opts === 'object' ? opts : {}) })
  }
  
  post(url, data) {
    const opts = arguments.length >= 3 ? arguments[2] : null
    return this.request({ url, method: 'POST', data, ...(opts && typeof opts === 'object' ? opts : {}) })
  }
  
  put(url, data) {
    const opts = arguments.length >= 3 ? arguments[2] : null
    return this.request({ url, method: 'PUT', data, ...(opts && typeof opts === 'object' ? opts : {}) })
  }
  
  delete(url) {
    const opts = arguments.length >= 2 ? arguments[1] : null
    return this.request({ url, method: 'DELETE', ...(opts && typeof opts === 'object' ? opts : {}) })
  }

  // 上传文件（用于头像等用户自定义资源）
  // - url: 例如 '/user/avatar/upload'（会自动拼到 BASE_URL=/api）
  // - filePath: uni.chooseImage 返回的临时路径
  // - opts: { name, formData, header, silent }
  upload(url, filePath) {
    const opts = arguments.length >= 3 ? arguments[2] : null
    const o = (opts && typeof opts === 'object') ? opts : {}

    return new Promise((resolve, reject) => {
      const token = uni.getStorageSync('token')
      const silent = !!o.silent
      const fullUrl = this.baseURL + url

      if (!filePath) {
        reject(new Error('缺少文件路径'))
        return
      }

      uni.uploadFile({
        url: fullUrl,
        filePath: String(filePath),
        name: String(o.name || 'file'),
        formData: (o.formData && typeof o.formData === 'object') ? o.formData : {},
        header: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          ...(o.header || {}),
        },
        timeout: REQUEST_TIMEOUT,
        success: (res) => {
          let payload = {}
          try {
            payload = typeof res.data === 'string' ? JSON.parse(res.data) : (res.data || {})
          } catch {
            payload = { _raw: String(res.data || '') }
          }

          if (res.statusCode === 200) {
            resolve(payload)
            return
          }

          if (res.statusCode === 401) {
            handleAuthExpired(token ? 'expired' : 'required')
            const err = new Error(NB_AUTH_REDIRECT_TOAST_TITLE)
            err.code = 'AUTH_EXPIRED'
            reject(err)
            return
          }

          const msg = payload?.error || payload?.message || `请求失败 (${res.statusCode})`
          if (!silent) {
            const log = res.statusCode >= 500 ? console.error : console.warn
            log(`[API ${res.statusCode}] ${fullUrl}`, msg)
          }
          const err = new Error(msg)
          err.status = res.statusCode
          err.url = fullUrl
          reject(err)
        },
        fail: (err) => {
          let errorMsg = '上传失败，请检查网络连接'
          const m = String(err?.errMsg || '')
          if (m.includes('timeout')) {
            errorMsg = '上传超时，请稍后重试'
          } else if (m) {
            errorMsg = m
          }
          reject(new Error(errorMsg))
        },
      })
    })
  }
}

export default new ApiClient()
