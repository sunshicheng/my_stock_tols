import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export default api

export const authApi = {
  register(phone, password) {
    return api.post('/api/auth/register', { phone, password })
  },
  login(phone, password) {
    return api.post('/api/auth/login', { phone, password })
  },
}

export const predictionsApi = {
  getToday() {
    return api.get('/api/predictions/today')
  },
  runPredict() {
    return api.post('/api/predictions/run', {}, { timeout: 600000 })
  },
  getHistory(startDate, endDate) {
    return api.get('/api/predictions/history', { params: { start_date: startDate, end_date: endDate } })
  },
  getDetail(tradeDate) {
    return api.get('/api/predictions/detail', { params: { trade_date: tradeDate } })
  },
}

export const positionsApi = {
  list() {
    return api.get('/api/positions')
  },
  add(data) {
    return api.post('/api/positions', data)
  },
  updatePlan(id, data) {
    return api.put(`/api/positions/${id}`, data)
  },
  remove(id) {
    return api.delete(`/api/positions/${id}`)
  },
}

export const backtestApi = {
  run(body) {
    return api.post('/api/backtest/run', body)
  },
}

export const configApi = {
  get() {
    return api.get('/api/config')
  },
  updateApiKey(apiKey) {
    return api.put('/api/config/api-key', { api_key: apiKey })
  },
  changePassword(oldPassword, newPassword) {
    return api.post('/api/config/change-password', { old_password: oldPassword, new_password: newPassword })
  },
}
