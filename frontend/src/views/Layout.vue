<template>
  <div class="layout">
    <main class="main">
      <router-view />
    </main>
    <nav class="bottom-nav">
      <router-link to="/" exact-active-class="active" class="nav-item">
        <span class="icon">📊</span>
        <span class="label">每日预测</span>
      </router-link>
      <router-link to="/positions" active-class="active" class="nav-item">
        <span class="icon">📁</span>
        <span class="label">持仓</span>
      </router-link>
      <router-link to="/history" active-class="active" class="nav-item">
        <span class="icon">📜</span>
        <span class="label">历史</span>
      </router-link>
      <router-link to="/config" active-class="active" class="nav-item">
        <span class="icon">⚙️</span>
        <span class="label">设置</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup>
</script>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  /* 底栏高度 + 安全区（刘海/Home 指示条） */
  padding-bottom: calc(56px + env(safe-area-inset-bottom, 0px));
}
.main {
  flex: 1;
  padding: 1rem;
  padding-bottom: 0.75rem;
  background: #f5f5f5;
  overflow: auto;
  -webkit-overflow-scrolling: touch;
}
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: calc(56px + env(safe-area-inset-bottom, 0px));
  padding-bottom: env(safe-area-inset-bottom, 0px);
  background: #fff;
  border-top: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-around;
  z-index: 100;
  box-shadow: 0 -2px 8px rgba(0,0,0,0.06);
}
.bottom-nav .nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-height: 48px;
  min-width: 56px;
  padding: 8px 12px;
  color: #666;
  text-decoration: none;
  font-size: 12px;
  border-radius: 8px;
  transition: color 0.2s, background 0.2s;
  -webkit-tap-highlight-color: transparent;
}
.bottom-nav .nav-item .icon {
  font-size: 22px;
}
.bottom-nav .nav-item:hover {
  color: #1989fa;
}
.bottom-nav .nav-item.active {
  color: #1989fa;
  background: rgba(25, 137, 250, 0.08);
}
</style>
