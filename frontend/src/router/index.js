import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { guest: true } },
  { path: '/register', name: 'Register', component: () => import('../views/Register.vue'), meta: { guest: true } },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    meta: { requiresAuth: true },
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

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) return next('/login')
  if (to.meta.guest && token && (to.name === 'Login' || to.name === 'Register')) return next('/')
  next()
})

export default router
