<template>
  <div class="page">
    <div class="header">
      <router-link to="/history" class="back">← 返回列表</router-link>
      <h1>预测与复盘 · {{ tradeDate }}</h1>
    </div>
    <div v-if="summary" class="summary">
      <span>股票 {{ summary.stock_hit }}/{{ summary.stock_total }} 命中</span>
      <span>基金 {{ summary.fund_hit }}/{{ summary.fund_total }} 命中</span>
      <span v-if="summary.avg_return != null">平均收益 {{ summary.avg_return }}%</span>
    </div>
    <section v-if="recommendations.length" class="section">
      <h2>当日推荐</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>类型</th>
              <th>代码</th>
              <th>名称</th>
              <th>风格</th>
              <th>评分</th>
              <th>理由</th>
              <th>AI 分析</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in recommendations" :key="r.code + (r.style || '')">
              <td>{{ r.category === 'fund' ? '基金' : '股票' }}</td>
              <td>{{ r.code }}</td>
              <td>{{ r.name }}</td>
              <td>{{ styleMap[r.style] || r.style }}</td>
              <td>{{ r.score }}</td>
              <td>{{ r.reason || '-' }}</td>
              <td class="analysis">{{ r.ai_analysis || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section v-if="reviews.length" class="section">
      <h2>复盘</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>推荐价</th>
              <th>收盘价</th>
              <th>涨跌幅</th>
              <th>命中</th>
              <th>AI 复盘</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in reviews" :key="r.code">
              <td>{{ r.code }}</td>
              <td>{{ r.name }}</td>
              <td>{{ r.recommend_price }}</td>
              <td>{{ r.close_price }}</td>
              <td>{{ r.change_pct != null ? r.change_pct + '%' : '-' }}</td>
              <td>{{ r.hit === 1 ? '涨' : '跌' }}</td>
              <td class="analysis">{{ r.ai_review || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section class="section">
      <h2>回测</h2>
      <div class="backtest-form">
        <input v-model="btStart" type="date" placeholder="开始日期" />
        <input v-model="btEnd" type="date" placeholder="结束日期" />
        <input v-model.number="btCash" type="number" step="10000" placeholder="初始资金" />
        <button type="button" class="btn primary" :disabled="btLoading" @click="runBacktest">运行回测</button>
      </div>
      <p v-if="btError" class="error">{{ btError }}</p>
      <div v-if="btResult" class="backtest-result">
        <p>区间 {{ btResult.start_date }} ~ {{ btResult.end_date }}</p>
        <p>总交易 {{ btResult.trade_count }} 次，总盈亏 {{ btResult.total_pnl }}，收益率 {{ btResult.total_return_pct }}%</p>
        <ul v-if="btResult.symbol_results && btResult.symbol_results.length">
          <li v-for="s in btResult.symbol_results.slice(0, 15)" :key="s.code">{{ s.code }} 交易{{ s.trade_count }}次 盈亏{{ s.total_pnl }} 收益{{ s.total_return_pct }}%</li>
        </ul>
      </div>
    </section>
    <div v-if="loading" class="loading">加载中…</div>
    <div v-else-if="!tradeDate" class="empty">未选择日期</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { predictionsApi, backtestApi } from '../api'

const route = useRoute()
const tradeDate = computed(() => route.params.date || '')
const summary = ref(null)
const recommendations = ref([])
const reviews = ref([])
const loading = ref(true)
const styleMap = { aggressive: '激进', stable: '稳健', moderate: '适中' }

const btStart = ref('')
const btEnd = ref('')
const btCash = ref(100000)
const btLoading = ref(false)
const btError = ref('')
const btResult = ref(null)

onMounted(async () => {
  if (!tradeDate.value) {
    loading.value = false
    return
  }
  try {
    const { data } = await predictionsApi.getDetail(tradeDate.value)
    summary.value = data.summary || null
    recommendations.value = data.recommendations || []
    reviews.value = data.reviews || []
    if (!btStart.value) btStart.value = tradeDate.value
    if (!btEnd.value) btEnd.value = tradeDate.value
  } finally {
    loading.value = false
  }
})

async function runBacktest() {
  btError.value = ''
  btResult.value = null
  if (!btStart.value || !btEnd.value) {
    btError.value = '请选择开始和结束日期'
    return
  }
  btLoading.value = true
  try {
    const res = await backtestApi.run({
      start_date: btStart.value,
      end_date: btEnd.value,
      cash: btCash.value || 100000,
      max_symbols: 20,
    })
    if (res.data.error) {
      btError.value = res.data.error
    } else {
      btResult.value = res.data
    }
  } catch (e) {
    btError.value = e.response?.data?.detail || '回测请求失败'
  } finally {
    btLoading.value = false
  }
}
</script>

<style scoped>
  .page { max-width: 100%; }
  .header { margin-bottom: 1rem; }
  .back { color: #1989fa; text-decoration: none; font-size: 14px; }
  .back:hover { text-decoration: underline; }
  .page h1 { margin: 0.5rem 0 1rem; font-size: 1.25rem; }
  .summary { display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem; font-size: 14px; color: #555; }
  .section { margin-bottom: 2rem; }
  .section h2 { font-size: 1rem; margin: 0 0 0.75rem; }
  .table-wrap { overflow: auto; background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 1rem; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }
  th { background: #fafafa; font-weight: 600; }
  .analysis { max-width: 320px; white-space: pre-wrap; word-break: break-all; }
  .backtest-form { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 10px; }
  .backtest-form input { padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; }
  .btn { padding: 8px 14px; border-radius: 6px; border: none; cursor: pointer; font-size: 13px; }
  .btn.primary { background: #1989fa; color: #fff; }
  .btn:disabled { opacity: 0.7; cursor: not-allowed; }
  .error { color: #e74c3c; font-size: 13px; margin: 0 0 8px; }
  .backtest-result { background: #f9f9f9; padding: 1rem; border-radius: 8px; font-size: 14px; }
  .backtest-result ul { margin: 0.5rem 0 0; padding-left: 1.5rem; }
  .loading, .empty { padding: 2rem; text-align: center; color: #666; }
</style>
