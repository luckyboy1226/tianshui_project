/**
 * HTTP请求工具
 * 基于axios封装，处理认证、错误、拦截器等
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'
import { API_CONFIG, API_ENDPOINTS, buildApiUrl } from '../config/api.js'

// 创建axios实例
const http = axios.create({
  timeout: API_CONFIG.TIMEOUT,
  headers: API_CONFIG.HEADERS,
  withCredentials: true, // 支持跨域携带cookie
})

let csrfBootstrapPromise = null

// 从 cookie 读取 csrftoken（适用于 Django）
function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
  return null
}

async function ensureCsrfCookie() {
  if (getCookie('csrftoken')) {
    return getCookie('csrftoken')
  }

  if (!csrfBootstrapPromise) {
    csrfBootstrapPromise = http.get(buildApiUrl(API_ENDPOINTS.AUTH.CSRF), {
      skipAuth: true,
      silentError: true,
    }).catch((error) => {
      throw error
    }).finally(() => {
      csrfBootstrapPromise = null
    })
  }

  await csrfBootstrapPromise
  return getCookie('csrftoken')
}

async function buildUnsafeRequestConfig(config = {}) {
  let csrfToken = getCookie('csrftoken')
  if (!csrfToken) {
    try {
      csrfToken = await ensureCsrfCookie()
    } catch (error) {
      console.warn('构建写请求时获取 CSRF Cookie 失败:', error)
    }
  }

  const nextHeaders = {
    ...(config.headers || {}),
    'X-Requested-With': 'XMLHttpRequest',
  }
  if (csrfToken) {
    nextHeaders['X-CSRFToken'] = csrfToken
  }

  return {
    ...config,
    headers: nextHeaders,
  }
}

// 请求拦截器
http.interceptors.request.use(
  async (config) => {
    if (!config.headers) {
      config.headers = {}
    }

    // 添加认证token
    const token = localStorage.getItem('access_token')
    const skipAuth = Boolean(config.skipAuth)
    const isTemporaryToken = token === 'temporary_dev_token_for_testing'
    if (skipAuth || isTemporaryToken) {
      delete config.headers.Authorization
    } else if (token) {
      config.headers.Authorization = `Token ${token}`
    }
    
    // 为非安全方法自动附带 CSRF Token（Django SessionAuthentication 需要）
    const method = (config.method || 'get').toLowerCase()
    if (['post', 'put', 'patch', 'delete'].includes(method)) {
      let csrfToken = getCookie('csrftoken')
      const isCsrfBootstrapRequest = typeof config.url === 'string' && config.url.includes(API_ENDPOINTS.AUTH.CSRF)
      if (!csrfToken && !isCsrfBootstrapRequest) {
        try {
          csrfToken = await ensureCsrfCookie()
        } catch (error) {
          console.warn('自动获取 CSRF Cookie 失败，后续写请求可能被后端拒绝:', error)
        }
      }
      if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken
      }
      // 提示后端这是XHR请求（某些中间件会用到）
      config.headers['X-Requested-With'] = 'XMLHttpRequest'
    }

    // 添加请求时间戳
    config.headers['X-Request-Time'] = Date.now()
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
http.interceptors.response.use(
  (response) => {
    // 直接返回响应数据
    return response.data
  },
  (error) => {
    // 错误处理
    const { response } = error
    const silentError = Boolean(error.config?.silentError)
    
    if (response && !silentError) {
      const { status, data } = response
      const message = data?.error || data?.detail || data?.message
      
      switch (status) {
        case 400:
          ElMessage.error(message || '请求参数错误')
          break
        case 401:
          ElMessage.error(message || '未授权，请重新登录')
          // 清除token并跳转到登录页
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          break
        case 403:
          ElMessage.error(message || '权限不足')
          break
        case 404:
          ElMessage.error(message || '请求的资源不存在')
          break
        case 500:
          ElMessage.error(message || '服务器内部错误')
          break
        default:
          ElMessage.error(message || '请求失败')
      }
    } else if (!silentError) {
      ElMessage.error('网络错误，请检查网络连接')
    }
    
    return Promise.reject(error)
  }
)

// 通用请求方法
export const request = {
  // GET请求
  get(url, params = {}, config = {}) {
    return http.get(url, { params, ...config })
  },
  
  // POST请求
  async post(url, data = {}, config = {}) {
    const nextConfig = await buildUnsafeRequestConfig(config)
    return http.post(url, data, nextConfig)
  },
  
  // PUT请求
  async put(url, data = {}, config = {}) {
    const nextConfig = await buildUnsafeRequestConfig(config)
    return http.put(url, data, nextConfig)
  },
  
  // DELETE请求
  async delete(url, config = {}) {
    const nextConfig = await buildUnsafeRequestConfig(config)
    return http.delete(url, nextConfig)
  },
  
  // 文件上传
  async upload(url, formData, config = {}) {
    const nextConfig = await buildUnsafeRequestConfig({
      // 不手动设置Content-Type，让浏览器自动设置boundary
      headers: {
        // 移除默认的Content-Type，让浏览器自动设置multipart/form-data
        'Content-Type': undefined,
      },
      ...config,
    })
    return http.post(url, formData, nextConfig)
  },
  
  // 文件下载
  download(url, params = {}, filename = 'download') {
    return http.get(url, {
      params,
      responseType: 'blob',
    }).then((data) => {
      const blob = new Blob([data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      window.URL.revokeObjectURL(url)
    })
  }
}

// 导出axios实例和请求方法
export { http }
export { ensureCsrfCookie }
export default request
