import axios from 'axios'
import { getToken, logout } from './auth'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000 //30s
})

// 请求拦截器：自动带上 token
service.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：统一处理 401（登录失效）和错误提示
service.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    if (error.response?.status === 401) {
      // token 失效或被禁用：清理本地登录态并跳转登录页
      logout()
      if (!location.pathname.startsWith('/login')) {
        location.href = '/login'
      }
      return Promise.reject(error)
    }

    // 优先展示后端返回的 message
    const msg = error.response?.data?.message || error.message || '网络异常，请稍后重试'
    error.message = msg
    console.error('请求发生错误:', msg)
    return Promise.reject(error)
  }
)

export default service
