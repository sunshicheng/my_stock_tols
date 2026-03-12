<template>
  <div class="page">
    <h1>我的持仓</h1>
    <div class="toolbar">
      <button type="button" class="btn primary" @click="showAdd = true">添加持仓</button>
    </div>
    <div v-if="loading" class="loading">加载中…</div>
    <div v-else-if="!items.length" class="empty">暂无持仓</div>
    <div v-else class="table-wrap">
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
  .btn { padding: 8px 14px; border-radius: 6px; border: none; cursor: pointer; font-size: 13px; }
  .btn.primary { background: #1989fa; color: #fff; }
  .btn.small { padding: 4px 10px; margin-right: 6px; background: #f0f0f0; }
  .btn.small.danger { background: #fee; color: #c00; }
  .loading, .empty { padding: 2rem; text-align: center; color: #666; }
  .table-wrap { overflow: auto; background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }
  th { background: #fafafa; font-weight: 600; }
  .modal { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
  .modal-content { background: #fff; padding: 1.5rem; border-radius: 8px; min-width: 360px; max-width: 90%; }
  .modal-content h3 { margin: 0 0 1rem; }
  .row { display: flex; gap: 10px; margin-bottom: 10px; }
  .row input, .row select { flex: 1; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; }
  .actions { margin-top: 1rem; display: flex; gap: 10px; justify-content: flex-end; }
  .actions button { padding: 8px 16px; border-radius: 6px; cursor: pointer; }
  .actions button[type="button"] { background: #f0f0f0; border: none; }
  .actions button[type="submit"] { background: #1989fa; color: #fff; border: none; }
</style>
