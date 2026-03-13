<template>
  <div class="page">
    <h1>设置</h1>
    <div class="card">
      <h3>AI 配置</h3>
      <p class="muted">分析功能需自行配置 API Key，支持 DeepSeek、OpenAI、Claude；使用 LiteLLM 时可选「自定义」并填写代理地址。</p>
      <div class="row">
        <label>提供商</label>
        <select v-model="provider" @change="applyPreset">
          <option value="deepseek">DeepSeek</option>
          <option value="openai">OpenAI</option>
          <option value="claude">Claude (Anthropic)</option>
          <option value="custom">自定义 / LiteLLM</option>
        </select>
      </div>
      <div class="row">
        <label>API Key</label>
        <input v-model="form.api_key" type="password" placeholder="输入 API Key 后保存" />
      </div>
      <div class="row">
        <label>Base URL <span class="optional">（可选）</span></label>
        <input v-model="form.base_url" type="text" placeholder="留空则使用提供商默认地址" />
      </div>
      <div class="row">
        <label>模型</label>
        <input v-model="form.model" type="text" placeholder="如 deepseek-chat、gpt-4、claude-3-5-sonnet" />
      </div>
      <p v-if="saveMsg" :class="saveOk ? 'ok' : 'error'">{{ saveMsg }}</p>
      <button type="button" class="btn primary touch-btn" :disabled="saving" @click="save">保存</button>
      <p class="hint">保存后写入项目 .env，后端或 CLI 下次启动后生效。</p>
    </div>
    <div v-if="loading" class="loading">加载中…</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { configApi } from '../api'

const PRESETS = {
  deepseek: { base_url: 'https://api.deepseek.com', model: 'deepseek-chat' },
  openai: { base_url: 'https://api.openai.com/v1', model: 'gpt-4o' },
  claude: { base_url: 'https://api.anthropic.com', model: 'claude-3-5-sonnet-20241022' },
  custom: { base_url: '', model: '' },
}

const provider = ref('deepseek')
const form = reactive({ api_key: '', base_url: '', model: '' })
const loading = ref(true)
const saving = ref(false)
const saveMsg = ref('')
const saveOk = ref(false)

onMounted(async () => {
  try {
    const { data } = await configApi.get()
    form.base_url = data.ai_base_url || ''
    form.model = data.ai_model || ''
    form.api_key = ''
    const u = (data.ai_base_url || '').toLowerCase()
    const m = (data.ai_model || '').toLowerCase()
    if (u.includes('deepseek')) provider.value = 'deepseek'
    else if (u.includes('openai')) provider.value = 'openai'
    else if (u.includes('anthropic')) provider.value = 'claude'
    else provider.value = 'custom'
  } finally {
    loading.value = false
  }
})

function applyPreset() {
  const p = PRESETS[provider.value]
  if (p) {
    form.base_url = p.base_url
    form.model = p.model
  }
}

async function save() {
  saveMsg.value = ''
  saving.value = true
  try {
    await configApi.update({
      api_key: form.api_key.trim() || undefined,
      base_url: form.base_url.trim() || undefined,
      model: form.model.trim() || undefined,
    })
    saveOk.value = true
    saveMsg.value = '已保存，重启后端或 CLI 后生效'
    form.api_key = ''
  } catch (e) {
    saveOk.value = false
    saveMsg.value = e.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page { max-width: 560px; }
.page h1 { margin: 0 0 1rem; font-size: 1.25rem; }
.card { background: #fff; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 1.5rem; }
.card h3 { margin: 0 0 0.75rem; font-size: 1rem; }
.muted { color: #666; font-size: 13px; margin: 0 0 12px; line-height: 1.4; }
.row { margin-bottom: 12px; }
.row label { display: block; font-size: 13px; color: #333; margin-bottom: 4px; }
.row .optional { color: #999; font-weight: normal; }
.row input, .row select { width: 100%; padding: 12px 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box; }
.btn { padding: 12px 20px; border-radius: 8px; border: none; cursor: pointer; font-size: 14px; margin-top: 8px; touch-action: manipulation; }
.btn.primary { background: #1989fa; color: #fff; }
.touch-btn { min-height: 44px; }
.btn:disabled { opacity: 0.7; cursor: not-allowed; }
.hint, .error, .ok { font-size: 13px; margin: 8px 0 0; }
.hint { color: #666; }
.error { color: #e74c3c; }
.ok { color: #07c160; }
.loading { padding: 2rem; text-align: center; color: #666; }
</style>
