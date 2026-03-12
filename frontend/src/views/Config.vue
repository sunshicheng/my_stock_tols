<template>
  <div class="page">
    <h1>配置</h1>
    <div class="card">
      <h3>DeepSeek API Key</h3>
      <p class="muted">当前显示：{{ config.deepseek_api_key_masked || '未设置' }}</p>
      <div class="row">
        <input v-model="apiKey" type="password" placeholder="输入新 API Key 后保存" />
        <button type="button" class="btn primary" :disabled="savingKey" @click="saveApiKey">保存</button>
      </div>
      <p class="hint">保存后将写入项目 .env，CLI 或后端下次启动时生效。</p>
    </div>
    <div class="card">
      <h3>修改密码</h3>
      <form @submit.prevent="changePw">
        <div class="row">
          <input v-model="pw.old" type="password" placeholder="原密码" />
        </div>
        <div class="row">
          <input v-model="pw.new" type="password" placeholder="新密码（至少6位）" />
        </div>
        <div class="row">
          <input v-model="pw.confirm" type="password" placeholder="确认新密码" />
        </div>
        <p v-if="pwError" class="error">{{ pwError }}</p>
        <p v-if="pwOk" class="ok">密码已修改</p>
        <button type="submit" class="btn primary" :disabled="savingPw">修改密码</button>
      </form>
    </div>
    <div v-if="loading" class="loading">加载中…</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { configApi } from '../api'

const config = ref({ deepseek_api_key_masked: '' })
const apiKey = ref('')
const savingKey = ref(false)
const loading = ref(true)
const pw = reactive({ old: '', new: '', confirm: '' })
const pwError = ref('')
const pwOk = ref(false)
const savingPw = ref(false)

onMounted(async () => {
  try {
    const { data } = await configApi.get()
    config.value = data
  } finally {
    loading.value = false
  }
})

async function saveApiKey() {
  if (!apiKey.value.trim()) return
  savingKey.value = true
  try {
    await configApi.updateApiKey(apiKey.value.trim())
    apiKey.value = ''
    const { data } = await configApi.get()
    config.value = data
  } finally {
    savingKey.value = false
  }
}

async function changePw() {
  pwError.value = ''
  pwOk.value = false
  if (!pw.old || !pw.new) {
    pwError.value = '请填写原密码和新密码'
    return
  }
  if (pw.new.length < 6) {
    pwError.value = '新密码至少 6 位'
    return
  }
  if (pw.new !== pw.confirm) {
    pwError.value = '两次新密码不一致'
    return
  }
  savingPw.value = true
  try {
    await configApi.changePassword(pw.old, pw.new)
    pwOk.value = true
    pw.old = pw.new = pw.confirm = ''
  } catch (e) {
    pwError.value = e.response?.data?.detail || '修改失败'
  } finally {
    savingPw.value = false
  }
}
</script>

<style scoped>
  .page { max-width: 560px; }
  .page h1 { margin: 0 0 1rem; font-size: 1.25rem; }
  .card { background: #fff; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 1.5rem; }
  .card h3 { margin: 0 0 0.75rem; font-size: 1rem; }
  .muted { color: #666; font-size: 14px; margin: 0 0 10px; }
  .row { margin-bottom: 10px; display: flex; gap: 10px; align-items: center; }
  .row input { flex: 1; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; }
  .btn { padding: 8px 14px; border-radius: 6px; border: none; cursor: pointer; font-size: 13px; }
  .btn.primary { background: #1989fa; color: #fff; }
  .btn:disabled { opacity: 0.7; cursor: not-allowed; }
  .hint, .error, .ok { font-size: 13px; margin: 8px 0 0; }
  .hint { color: #666; }
  .error { color: #e74c3c; }
  .ok { color: #07c160; }
  .loading { padding: 2rem; text-align: center; color: #666; }
</style>
