// API请求封装（统一：支持 GET query、H5 优先 fetch、其他平台回退 uni.request）
import config from './config.js'

const API_PREFIX = '/api'
const rawBaseURL = String(config?.baseURL || '').replace(/\/+$/, '')
const BASE_URL = rawBaseURL.endsWith(API_PREFIX) ? rawBaseURL : rawBaseURL + API_PREFIX
const REQUEST_TIMEOUT = config?.timeout || 30000
const isDev = typeof process !== 'undefined'
  ? process.env?.NODE_ENV !== 'production'
  : false

function toQueryString(data) {
  if (!data || typeof data !== 'object') return ''
  const pairs = []
  for (const [key, value] of Object.entries(data)) {
    if (value === undefined || value === null || value === '') continue
    pairs.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
  }
  return pairs.length ? pairs.join('&') : ''
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

      if (isDev) {
        // 控制台噪音会显著增加排障成本，这里仅在开发态打印关键字段
        console.log(`[API] ${method} ${fullUrl}`, data)
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
              uni.removeStorageSync('token')
              uni.reLaunch({
                url: '/pages/login/index'
              })
              reject(new Error('未登录或登录已过期'))
            } else {
              const errorMsg = resBody?.error || resBody?.message || `请求失败 (${response.status})`
              console.error(`[API错误-fetch] ${fullUrl}`, errorMsg)
              reject(new Error(errorMsg))
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
          // Token过期，跳转登录
          uni.removeStorageSync('token')
          uni.reLaunch({
            url: '/pages/login/index'
          })
          reject(new Error('未登录或登录已过期'))
        } else {
          const errorMsg = res.data?.error || res.data?.message || `请求失败 (${res.statusCode})`
          console.error(`[API错误] ${fullUrl}`, errorMsg)
          reject(new Error(errorMsg))
        }
      },
      fail: (err) => {
        // 处理各种错误情况
        console.error(`[API失败] ${fullUrl}`, err)
        
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
    return this.request({ url, method: 'GET', data })
  }
  
  post(url, data) {
    return this.request({ url, method: 'POST', data })
  }
  
  put(url, data) {
    return this.request({ url, method: 'PUT', data })
  }
  
  delete(url) {
    return this.request({ url, method: 'DELETE' })
  }
}

export default new ApiClient()
