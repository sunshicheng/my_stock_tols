<template>
  <div class="page">
    <h1>当日预测</h1>
    <p class="date">交易日：{{ tradeDate }}</p>

    <!-- 一、今日推荐（预测） -->
    <section class="block">
      <h2 class="block-title">今日推荐（预测）</h2>
      <div v-if="loading" class="loading">加载中…</div>
      <template v-else>
        <!-- 预测报告文档（卦象、操作建议、要闻、驱动板块、推荐等） -->
        <div v-if="reportContent" class="report-section">
          <div class="report-body markdown" v-html="formattedReport"></div>
        </div>
        <!-- 无报告时仅表格；有报告时也保留表格便于快速查看 -->
        <div v-if="!recommendations.length" class="empty">暂无今日推荐，请先运行 CLI 生成预测。</div>
        <div v-else class="table-wrap">
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
      </template>
    </section>

    <!-- 二、复盘 -->
    <section class="block">
      <h2 class="block-title">复盘</h2>
      <div v-if="summary" class="stats-row">
        <div class="stat-card">
          <span class="stat-label">股票命中</span>
          <span class="stat-value">{{ summary.stock_hit }}/{{ summary.stock_total }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">基金命中</span>
          <span class="stat-value">{{ summary.fund_hit }}/{{ summary.fund_total }}</span>
        </div>
        <div class="stat-card" v-if="summary.avg_return != null">
          <span class="stat-label">平均收益</span>
          <span class="stat-value" :class="summary.avg_return >= 0 ? 'positive' : 'negative'">
            {{ summary.avg_return }}%
          </span>
        </div>
      </div>
      <div v-if="summary && summary.summary && summary.summary !== '待复盘'" class="review-section">
        <h3 class="review-title">投资复盘总结</h3>
        <div class="review-body markdown" v-html="formattedSummary"></div>
      </div>
      <p v-else-if="summary && summary.summary === '待复盘'" class="pending">当日尚未复盘，复盘后将显示总结。</p>
      <p v-else-if="!summary" class="pending">暂无复盘数据。</p>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { parse } from 'marked'
import { predictionsApi } from '../api'

const tradeDate = ref('')
const summary = ref(null)
const recommendations = ref([])
const reportContent = ref(null)
const loading = ref(true)
const styleMap = { aggressive: '激进', stable: '稳健', moderate: '适中' }

const mdOptions = { gfm: true, breaks: true }

const formattedSummary = computed(() => {
  const text = summary.value?.summary
  if (!text || typeof text !== 'string') return ''
  return parse(text, mdOptions)
})

const formattedReport = computed(() => {
  const text = reportContent.value
  if (!text || typeof text !== 'string') return ''
  return parse(text, mdOptions)
})

onMounted(async () => {
  try {
    const { data } = await predictionsApi.getToday()
    tradeDate.value = data.trade_date
    summary.value = data.summary || null
    recommendations.value = data.recommendations || []
    reportContent.value = data.report_content || null
  } catch (_) {
    recommendations.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
  .page { max-width: 100%; }
  .page h1 { margin: 0 0 0.25rem; font-size: 1.35rem; }
  .date { color: #666; font-size: 14px; margin: 0 0 1rem; }

  .block { margin-bottom: 2rem; }
  .block-title { margin: 0 0 1rem; font-size: 1rem; font-weight: 600; color: #333; padding-bottom: 0.5rem; border-bottom: 1px solid #eee; }

  .report-section {
    background: #fff;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border: 1px solid #eee;
  }
  .report-body { font-size: 14px; line-height: 1.65; color: #444; }
  .report-body.markdown :deep(p) { margin: 0 0 0.6em; }
  .report-body.markdown :deep(p:last-child) { margin-bottom: 0; }
  .report-body.markdown :deep(strong) { color: #222; font-weight: 600; }
  .report-body.markdown :deep(h1) { font-size: 1.15rem; margin: 1em 0 0.5em; font-weight: 600; }
  .report-body.markdown :deep(h2) { font-size: 1.08rem; margin: 0.9em 0 0.4em; font-weight: 600; }
  .report-body.markdown :deep(h3) { font-size: 1rem; margin: 0.8em 0 0.4em; font-weight: 600; }
  .report-body.markdown :deep(h4) { font-size: 0.95rem; margin: 0.7em 0 0.3em; font-weight: 600; }
  .report-body.markdown :deep(ul) { margin: 0.5em 0; padding-left: 1.5em; }
  .report-body.markdown :deep(ol) { margin: 0.5em 0; padding-left: 1.5em; }
  .report-body.markdown :deep(li) { margin-bottom: 0.25em; }
  .report-body.markdown :deep(table) { border-collapse: collapse; width: 100%; margin: 0.5em 0; font-size: 13px; }
  .report-body.markdown :deep(th), .report-body.markdown :deep(td) { padding: 6px 10px; text-align: left; border: 1px solid #eee; }
  .report-body.markdown :deep(th) { background: #fafafa; font-weight: 600; }

  .stats-row { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 1rem; }
  .stat-card {
    background: #fff;
    border-radius: 10px;
    padding: 12px 20px;
    min-width: 120px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border: 1px solid #eee;
    display: flex; flex-direction: column; gap: 4px;
  }
  .stat-label { font-size: 12px; color: #888; }
  .stat-value { font-size: 1.1rem; font-weight: 600; color: #333; }
  .stat-value.positive { color: #07c160; }
  .stat-value.negative { color: #ee0a24; }

  .review-section {
    background: #fff;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border: 1px solid #eee;
  }
  .review-title { margin: 0 0 0.75rem; font-size: 1rem; color: #333; font-weight: 600; }
  .review-body { font-size: 14px; line-height: 1.65; color: #444; }
  .review-body.markdown :deep(p) { margin: 0 0 0.6em; }
  .review-body.markdown :deep(p:last-child) { margin-bottom: 0; }
  .review-body.markdown :deep(strong) { color: #222; font-weight: 600; }
  .review-body.markdown :deep(h1) { font-size: 1.1rem; margin: 1em 0 0.5em; font-weight: 600; }
  .review-body.markdown :deep(h2) { font-size: 1.05rem; margin: 0.9em 0 0.4em; font-weight: 600; }
  .review-body.markdown :deep(h3) { font-size: 1rem; margin: 0.8em 0 0.4em; font-weight: 600; }
  .review-body.markdown :deep(h4) { font-size: 0.95rem; margin: 0.7em 0 0.3em; font-weight: 600; }
  .review-body.markdown :deep(ul) { margin: 0.5em 0; padding-left: 1.5em; }
  .review-body.markdown :deep(ol) { margin: 0.5em 0; padding-left: 1.5em; }
  .review-body.markdown :deep(li) { margin-bottom: 0.25em; }
  .pending { font-size: 14px; color: #888; margin: 0 0 1rem; }

  .loading, .empty { padding: 2rem; text-align: center; color: #666; }
  .table-wrap { overflow: auto; background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }
  th { background: #fafafa; font-weight: 600; }
  .analysis { max-width: 320px; white-space: pre-wrap; word-break: break-all; }
</style>
