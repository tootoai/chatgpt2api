import axios, { type AxiosError, type AxiosInstance } from 'axios'

export const AUTH_TOKEN_STORAGE_KEY = 'chatgpt2api.adminKey'

export function getAuthToken() {
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || ''
}

export function setAuthToken(token: string) {
  const cleanToken = token.trim()
  if (cleanToken) {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, cleanToken)
    return
  }
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
}

export function clearAuthToken() {
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
}

type UnauthorizedHandler = () => void | Promise<void>

let unauthorizedHandler: UnauthorizedHandler | null = null

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  unauthorizedHandler = handler
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 60000,
})

let isRedirectingToLogin = false

function extractErrorMessage(data: unknown, fallback: string) {
  if (typeof data === 'string') return data
  if (!data || typeof data !== 'object') return fallback

  const payload = data as Record<string, any>
  const detail = payload.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') {
    if (typeof detail.error === 'string') return detail.error
    if (typeof detail.message === 'string') return detail.message
  }
  if (payload.error && typeof payload.error === 'object' && typeof payload.error.message === 'string') {
    return payload.error.message
  }
  if (typeof payload.error === 'string') return payload.error
  if (typeof payload.message === 'string') return payload.message
  return fallback
}

apiClient.interceptors.request.use(
  (config) => {
    const token = getAuthToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

apiClient.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError) => {
    const status = error.response?.status
    const requestUrl = String(error.config?.url || '')
    const isAuthProbe = requestUrl.includes('/auth/status')
    const isLoginRequest = requestUrl.includes('/auth/login')

    if (status === 401 && !isLoginRequest && !isAuthProbe) {
      const onLoginPage = window.location.hash.startsWith('#/login')
      if (!onLoginPage && !isRedirectingToLogin) {
        isRedirectingToLogin = true
        clearAuthToken()
        Promise.resolve(unauthorizedHandler?.())
          .catch(() => {})
          .finally(() => {
            window.setTimeout(() => {
              isRedirectingToLogin = false
            }, 200)
          })
      }
    }

    const errorMessage = extractErrorMessage(error.response?.data, error.message)

    const wrapped = new Error(errorMessage || 'Request failed') as Error & {
      status?: number
      data?: unknown
    }
    wrapped.status = error.response?.status
    wrapped.data = error.response?.data
    return Promise.reject(wrapped)
  },
)

export default apiClient
