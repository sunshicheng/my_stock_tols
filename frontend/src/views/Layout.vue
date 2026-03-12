<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">股票推荐</div>
      <nav>
        <router-link to="/" exact-active-class="active">首页·每日预测</router-link>
        <router-link to="/positions" active-class="active">我的持仓</router-link>
        <router-link to="/history" active-class="active">历史预测</router-link>
        <router-link to="/config" active-class="active">配置</router-link>
      </nav>
      <div class="user">
        <span>{{ userPhone }}</span>
        <button type="button" @click="logout">退出</button>
      </div>
    </aside>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const userPhone = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}').phone || ''
  } catch {
    return ''
  }
})

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}
</script>

<style scoped>
  .layout { display: flex; min-height: 100vh; }
  .sidebar { width: 200px; background: #2c3e50; color: #ecf0f1; padding: 1rem 0; display: flex; flex-direction: column; }
  .brand { padding: 0 1rem 1rem; font-weight: 600; font-size: 1.1rem; border-bottom: 1px solid #34495e; margin-bottom: 1rem; }
  .sidebar nav { flex: 1; }
  .sidebar nav a { display: block; padding: 10px 1rem; color: #bdc3c7; text-decoration: none; font-size: 14px; }
  .sidebar nav a:hover { background: #34495e; color: #fff; }
  .sidebar nav a.active { background: #1989fa; color: #fff; }
  .user { padding: 1rem; border-top: 1px solid #34495e; font-size: 13px; display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .user button { padding: 4px 10px; background: transparent; border: 1px solid #7f8c8d; color: #bdc3c7; border-radius: 4px; cursor: pointer; font-size: 12px; }
  .user button:hover { color: #fff; border-color: #95a5a6; }
  .main { flex: 1; padding: 1.5rem; background: #f5f5f5; overflow: auto; }
</style>
