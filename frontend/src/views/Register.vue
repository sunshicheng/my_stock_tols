<template>
  <div class="register-page">
    <div class="card">
      <h1>注册</h1>
      <form @submit.prevent="submit">
        <input v-model="phone" type="tel" placeholder="手机号" maxlength="11" />
        <input v-model="password" type="password" placeholder="密码（至少6位）" />
        <input v-model="confirm" type="password" placeholder="确认密码" />
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" :disabled="loading">注册</button>
      </form>
      <p class="link"><router-link to="/login">已有账号？去登录</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '../api'

const router = useRouter()
const phone = ref('')
const password = ref('')
const confirm = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  if (!phone.value || !password.value) {
    error.value = '请填写手机号和密码'
    return
  }
  if (password.value.length < 6) {
    error.value = '密码至少 6 位'
    return
  }
  if (password.value !== confirm.value) {
    error.value = '两次密码不一致'
    return
  }
  loading.value = true
  try {
    const { data } = await authApi.register(phone.value, password.value)
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify({ id: data.user_id, phone: data.phone }))
    router.replace('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
  .register-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #e8e8e8; }
  .card { background: #fff; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); width: 320px; }
  .card h1 { margin: 0 0 1.5rem; font-size: 1.5rem; }
  .card input { width: 100%; padding: 10px 12px; margin-bottom: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
  .card button { width: 100%; padding: 10px; background: #1989fa; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
  .card button:disabled { opacity: 0.7; cursor: not-allowed; }
  .error { color: #e74c3c; font-size: 13px; margin: 0 0 8px; }
  .link { margin-top: 1rem; font-size: 13px; }
  .link a { color: #1989fa; }
</style>
