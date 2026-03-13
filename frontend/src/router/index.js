import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    children: [
      { path: '', name: 'Home', component: () => import('../views/Home.vue') },
      { path: 'positions', name: 'Positions', component: () => import('../views/Positions.vue') },
      { path: 'history', name: 'History', component: () => import('../views/History.vue') },
      { path: 'history/:date', name: 'HistoryDetail', component: () => import('../views/HistoryDetail.vue') },
      { path: 'config', name: 'Config', component: () => import('../views/Config.vue') },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

export default router
