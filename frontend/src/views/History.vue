<template>
  <div class="page">
    <h1>历史预测</h1>
    <div class="filters">
      <input v-model="startDate" type="date" />
      <span>至</span>
      <input v-model="endDate" type="date" />
      <button type="button" class="btn primary" @click="load">查询</button>
    </div>
    <div v-if="loading" class="loading">加载中…</div>
    <div v-else-if="!items.length" class="empty">暂无数据</div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>交易日</th>
            <th>股票命中</th>
            <th>基金命中</th>
            <th>平均收益</th>
            <th>摘要</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.trade_date">
            <td>{{ row.trade_date }}</td>
            <td>{{ row.stock_hit }}/{{ row.stock_total }}</td>
            <td>{{ row.fund_hit }}/{{ row.fund_total }}</td>
            <td>{{ row.avg_return != null ? row.avg_return + '%' : '-' }}</td>
            <td>{{ row.summary || '-' }}</td>
            <td>
              <router-link :to="'/history/' + row.trade_date" class="link">详情</router-link>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { predictionsApi } from '../api'

const startDate = ref('')
const endDate = ref('')
const items = ref([])
const loading = ref(false)

function defaultRange() {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 30)
  startDate.value = start.toISOString().slice(0, 10)
  endDate.value = end.toISOString().slice(0, 10)
}

async function load() {
  if (!startDate.value || !endDate.value) {
    defaultRange()
  }
  loading.value = true
  try {
    const { data } = await predictionsApi.getHistory(startDate.value, endDate.value)
    items.value = data.items || []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  defaultRange()
  load()
})
</script>

<style scoped>
  .page { max-width: 100%; }
  .page h1 { margin: 0 0 1rem; font-size: 1.25rem; }
  .filters { display: flex; align-items: center; gap: 10px; margin-bottom: 1rem; flex-wrap: wrap; }
  .filters input[type="date"] { padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; }
  .btn { padding: 8px 14px; border-radius: 6px; border: none; cursor: pointer; font-size: 13px; }
  .btn.primary { background: #1989fa; color: #fff; }
  .loading, .empty { padding: 2rem; text-align: center; color: #666; }
  .table-wrap { overflow: auto; background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }
  th { background: #fafafa; font-weight: 600; }
  .link { color: #1989fa; text-decoration: none; }
  .link:hover { text-decoration: underline; }
</style>
