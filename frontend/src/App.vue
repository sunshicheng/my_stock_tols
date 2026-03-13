<template>
  <router-view />
</template>

<script setup>
</script>

<style>
  * { box-sizing: border-box; }
  html {
    -webkit-text-size-adjust: 100%;
    -webkit-tap-highlight-color: transparent;
  }
  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: #f5f5f5;
    font-size: 14px;
    line-height: 1.5;
    /* 安全区，供固定底栏等使用 */
    padding-top: env(safe-area-inset-top);
    padding-left: env(safe-area-inset-left);
    padding-right: env(safe-area-inset-right);
  }
  #app { min-height: 100vh; }
  input, select, textarea {
    font-size: 16px; /* 避免 iOS 聚焦时缩放 */
  }
</style>
