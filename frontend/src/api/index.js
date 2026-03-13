import { ref } from 'vue'
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  headers: { 'Content-Type': 'application/json' },
  timeout: 8000, // 8 秒超时，网络异常时尽快提示（避免一直转圈）
})

/** 网络异常时的全局提示文案，由响应拦截器设置，App.vue 展示后自动清除 */
export const networkErrorMsg = ref('')

/** 当前为 Capacitor App 且未配置服务器地址时为 true，请求会发到 localhost 导致无效，需提示用户重新打包 */
export const isAppWithoutServer =
  typeof window !== 'undefined' &&
  !!window.Capacitor?.isNativePlatform?.() &&
  !(import.meta.env.VITE_API_BASE || '').trim()

/** 是否应视为网络/连接问题并展示统一提示（无响应 = 未连上或超时，含 Android WebView） */
function shouldShowNetworkTip(err) {
  if (!err) return false
  // 有 HTTP 响应（含 4xx/5xx）则按接口错误处理，不弹网络提示
  if (err.response != null) return false
  const msg = (err.message || '').toLowerCase()
  const code = err.code || err.errno
  if (
    msg.includes('network error') ||
    msg.includes('failed to fetch') ||
    msg.includes('timeout') ||
    code === 'ECONNABORTED' ||
    code === 'ERR_NETWORK' ||
    code === 'ETIMEDOUT' ||
    code === 'ECONNREFUSED'
  ) return true
  // 无 response 即未拿到任何响应（服务器未启动、断网等），Android WebView 里错误结构可能不同，统一提示
  return true
}

const NETWORK_MSG = '网络连接异常，请检查网络后重试'

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (shouldShowNetworkTip(err)) {
      err.message = NETWORK_MSG
      networkErrorMsg.value = NETWORK_MSG
      setTimeout(() => {
        networkErrorMsg.value = ''
      }, 6000)
    }
    return Promise.reject(err)
  }
)

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
