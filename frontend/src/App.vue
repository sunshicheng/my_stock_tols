<template>
  <div v-if="isAppWithoutServer" class="network-tip app-no-server">
    当前 App 未配置服务器地址，请用 <code>VITE_API_BASE=你的服务器</code> 重新打包后再安装。
  </div>
  <div v-else-if="networkErrorMsg" class="network-tip">
    {{ networkErrorMsg }}
  </div>
  <router-view />
</template>

<script setup>
import { networkErrorMsg, isAppWithoutServer } from './api'
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
  .network-tip {
    position: sticky;
    top: 0;
    z-index: 999;
    padding: 10px 12px;
    background: #ee0a24;
    color: #fff;
    font-size: 14px;
    text-align: center;
  }
  .network-tip.app-no-server {
    background: #ed6a0c;
    font-size: 13px;
    line-height: 1.4;
  }
  .network-tip code { font-size: 12px; opacity: 0.95; }
</style>
