<template>
  <div class="page">
    <h1>我的持仓</h1>
    <div class="toolbar">
      <button type="button" class="btn primary touch-btn" @click="showAdd = true">添加持仓</button>
    </div>
    <div v-if="loading" class="loading">加载中…</div>
    <div v-else-if="!items.length" class="empty">暂无持仓</div>
    <template v-else>
      <!-- 桌面：表格 -->
      <div class="table-wrap desktop-only">
        <table>
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>类型</th>
              <th>买入日</th>
              <th>买入价</th>
              <th>数量</th>
              <th>目标价</th>
              <th>止损</th>
              <th>计划卖出日</th>
              <th>备注</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in items" :key="p.id">
              <td>{{ p.code }}</td>
              <td>{{ p.name || p.code }}</td>
              <td>{{ p.category === 'fund' ? '基金' : '股票' }}</td>
              <td>{{ p.buy_date }}</td>
              <td>{{ p.buy_price }}</td>
              <td>{{ p.quantity }}</td>
              <td>{{ p.target_price ?? '-' }}</td>
              <td>{{ p.stop_loss ?? '-' }}</td>
              <td>{{ p.plan_sell_date || '-' }}</td>
              <td>{{ p.note || '-' }}</td>
              <td>
                <button type="button" class="btn small" @click="openPlan(p)">计划</button>
                <button type="button" class="btn small danger" @click="remove(p.id)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <!-- 移动端：卡片列表 -->
      <div class="card-list mobile-only">
        <div v-for="p in items" :key="p.id" class="position-card">
          <div class="card-row main">
            <span class="name">{{ p.name || p.code }}</span>
            <span class="code">{{ p.code }}</span>
            <span class="cat">{{ p.category === 'fund' ? '基金' : '股票' }}</span>
          </div>
          <div class="card-row">
            <span>买入 {{ p.buy_date }} · {{ p.buy_price }} 元 × {{ p.quantity }}</span>
          </div>
          <div v-if="p.target_price || p.stop_loss || p.plan_sell_date" class="card-row sub">
            目标 {{ p.target_price ?? '-' }} / 止损 {{ p.stop_loss ?? '-' }} / 计划卖出 {{ p.plan_sell_date || '-' }}
          </div>
          <div class="card-actions">
            <button type="button" class="btn small" @click="openPlan(p)">计划</button>
            <button type="button" class="btn small danger" @click="remove(p.id)">删除</button>
          </div>
        </div>
      </div>
    </template>

    <!-- 添加 -->
    <div v-if="showAdd" class="modal" @click.self="showAdd = false">
      <div class="modal-content">
        <h3>添加持仓</h3>
        <form @submit.prevent="add">
          <div class="row">
            <input v-model="form.code" placeholder="代码" required />
            <input v-model="form.name" placeholder="名称（可选）" />
          </div>
          <div class="row">
            <select v-model="form.category">
              <option value="stock">股票</option>
              <option value="fund">基金</option>
            </select>
            <input v-model="form.buy_date" type="date" placeholder="买入日期" required />
          </div>
          <div class="row">
            <input v-model.number="form.buy_price" type="number" step="0.01" placeholder="买入价" required />
            <input v-model.number="form.quantity" type="number" step="1" placeholder="数量" required />
          </div>
          <div class="row">
            <input v-model.number="form.target_price" type="number" step="0.01" placeholder="目标价（可选）" />
            <input v-model.number="form.stop_loss" type="number" step="0.01" placeholder="止损（可选）" />
          </div>
          <div class="row">
            <input v-model="form.plan_sell_date" type="date" placeholder="计划卖出日（可选）" />
            <input v-model="form.note" placeholder="备注（可选）" />
          </div>
          <div class="actions">
            <button type="button" @click="showAdd = false">取消</button>
            <button type="submit">确定</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 修改计划 -->
    <div v-if="planId" class="modal" @click.self="planId = null">
      <div class="modal-content">
        <h3>修改卖出计划</h3>
        <form @submit.prevent="savePlan">
          <div class="row">
            <input v-model.number="planForm.target_price" type="number" step="0.01" placeholder="目标价" />
            <input v-model.number="planForm.stop_loss" type="number" step="0.01" placeholder="止损" />
          </div>
          <div class="row">
            <input v-model="planForm.plan_sell_date" type="date" placeholder="计划卖出日" />
            <input v-model="planForm.note" placeholder="备注" />
          </div>
          <div class="actions">
            <button type="button" @click="planId = null">取消</button>
            <button type="submit">保存</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { positionsApi } from '../api'

const items = ref([])
const loading = ref(true)
const showAdd = ref(false)
const planId = ref(null)
const form = reactive({
  code: '', name: '', category: 'stock', buy_date: '', buy_price: '', quantity: '',
  target_price: '', stop_loss: '', plan_sell_date: '', note: '',
})
const planForm = reactive({ target_price: '', stop_loss: '', plan_sell_date: '', note: '' })

async function load() {
  loading.value = true
  try {
    const { data } = await positionsApi.list()
    items.value = data.items || []
  } finally {
    loading.value = false
  }
}

async function add() {
  await positionsApi.add({
    code: form.code,
    name: form.name,
    category: form.category,
    buy_date: form.buy_date,
    buy_price: form.buy_price,
    quantity: form.quantity,
    target_price: form.target_price || null,
    stop_loss: form.stop_loss || null,
    plan_sell_date: form.plan_sell_date || null,
    note: form.note || null,
  })
  showAdd.value = false
  Object.assign(form, { code: '', name: '', category: 'stock', buy_date: '', buy_price: '', quantity: '', target_price: '', stop_loss: '', plan_sell_date: '', note: '' })
  load()
}

function openPlan(p) {
  planId.value = p.id
  planForm.target_price = p.target_price ?? ''
  planForm.stop_loss = p.stop_loss ?? ''
  planForm.plan_sell_date = p.plan_sell_date || ''
  planForm.note = p.note || ''
}

async function savePlan() {
  await positionsApi.updatePlan(planId.value, {
    target_price: planForm.target_price || null,
    stop_loss: planForm.stop_loss || null,
    plan_sell_date: planForm.plan_sell_date || null,
    note: planForm.note || null,
  })
  planId.value = null
  load()
}

async function remove(id) {
  if (!confirm('确定删除该持仓？')) return
  await positionsApi.remove(id)
  load()
}

onMounted(load)
</script>

<style scoped>
  .page { max-width: 100%; }
  .page h1 { margin: 0 0 1rem; font-size: 1.25rem; }
  .toolbar { margin-bottom: 1rem; }
  .btn { padding: 8px 14px; border-radius: 8px; border: none; cursor: pointer; font-size: 13px; touch-action: manipulation; }
  .btn.primary { background: #1989fa; color: #fff; }
  .touch-btn { min-height: 44px; padding: 12px 20px; }
  .btn.small { padding: 8px 12px; margin-right: 8px; background: #f0f0f0; min-height: 36px; }
  .btn.small.danger { background: #fee; color: #c00; }
  .loading, .empty { padding: 2rem; text-align: center; color: #666; }
  .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  table { width: 100%; min-width: 800px; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }
  th { background: #fafafa; font-weight: 600; }

  .mobile-only { display: none; }
  @media (max-width: 768px) {
    .desktop-only { display: none !important; }
    .mobile-only { display: block; }
    .card-list { display: flex; flex-direction: column; gap: 12px; }
    .position-card {
      background: #fff; border-radius: 12px; padding: 1rem; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
      border: 1px solid #eee;
    }
    .position-card .card-row { margin-bottom: 6px; font-size: 14px; }
    .position-card .card-row.main { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .position-card .card-row.main .name { font-weight: 600; font-size: 1rem; }
    .position-card .card-row.main .code { color: #888; font-size: 13px; }
    .position-card .card-row.main .cat { font-size: 12px; color: #1989fa; background: rgba(25,137,250,0.1); padding: 2px 8px; border-radius: 4px; }
    .position-card .card-row.sub { font-size: 12px; color: #666; }
    .position-card .card-actions { margin-top: 12px; padding-top: 10px; border-top: 1px solid #f0f0f0; }
    .position-card .card-actions .btn { margin-right: 8px; }
  }

  .modal { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 1rem; overflow-y: auto; -webkit-overflow-scrolling: touch; }
  .modal-content { background: #fff; padding: 1.5rem; border-radius: 12px; width: 100%; max-width: 420px; max-height: 90vh; overflow-y: auto; }
  .modal-content h3 { margin: 0 0 1rem; font-size: 1.1rem; }
  .row { display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
  .row input, .row select { flex: 1; min-width: 0; padding: 12px 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 16px; }
  .actions { margin-top: 1.25rem; display: flex; gap: 12px; justify-content: flex-end; }
  .actions button { padding: 12px 20px; min-height: 44px; border-radius: 8px; cursor: pointer; font-size: 14px; touch-action: manipulation; }
  .actions button[type="button"] { background: #f0f0f0; border: none; }
  .actions button[type="submit"] { background: #1989fa; color: #fff; border: none; }
  @media (max-width: 480px) {
    .row { flex-direction: column; }
    .row input, .row select { flex: none; width: 100%; }
  }
</style>
