import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  headers: { 'Content-Type': 'application/json' },
})

export default api

export const predictionsApi = {
  getToday() {
    return api.get('/api/predictions/today')
  },
  /** 提交预测任务（后台异步），建议随后轮询 getPredictStatus */
  runPredict() {
    return api.post('/api/predictions/run', {}, { timeout: 15000 })
  },
  getPredictStatus() {
    return api.get('/api/predictions/run/status', { timeout: 10000 })
  },
  /** 提交复盘任务（后台异步），建议随后轮询 getReviewStatus */
  runReview(tradeDate) {
    const params = tradeDate ? { trade_date: tradeDate } : {}
    return api.post('/api/predictions/review/run', {}, { params, timeout: 15000 })
  },
  getReviewStatus() {
    return api.get('/api/predictions/review/status', { timeout: 10000 })
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
  update(body) {
    return api.put('/api/config', body)
  },
}
