import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/public/uptime',
      name: 'public-uptime',
      component: () => import('@/views/PublicUptime.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/public/logs',
      name: 'public-logs',
      component: () => import('@/views/PublicLogs.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      component: () => import('@/layouts/AppShell.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/Dashboard.vue'),
          meta: { keepAlive: true },
        },
        {
          path: 'accounts',
          name: 'accounts',
          component: () => import('@/views/Accounts.vue'),
          meta: { keepAlive: true },
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/Settings.vue'),
          meta: { keepAlive: true },
        },
        {
          path: 'proxy',
          name: 'proxy',
          component: () => import('@/views/Proxy.vue'),
          meta: { keepAlive: true },
        },
        {
          path: 'logs',
          name: 'logs',
          component: () => import('@/views/Logs.vue'),
          meta: { keepAlive: false },
        },
        {
          path: 'monitor',
          name: 'monitor',
          component: () => import('@/views/Monitor.vue'),
          meta: { keepAlive: true },
        },
        {
          path: 'docs',
          name: 'docs',
          component: () => import('@/views/Docs.vue'),
          meta: { keepAlive: false },
        },
        {
          path: 'gallery',
          name: 'gallery',
          component: () => import('@/views/Gallery.vue'),
          meta: { keepAlive: false },
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (to.name === 'login') {
    if (authStore.isLoggedIn) {
      return { name: 'dashboard' }
    }
    const loggedIn = await authStore.checkAuth()
    if (loggedIn) {
      return { name: 'dashboard' }
    }
    return true
  }

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth !== false)
  if (!requiresAuth) {
    return true
  }

  if (authStore.isLoggedIn) {
    // Fast path: don't block route switch on auth probe.
    void authStore.checkAuth()
    return true
  }

  const loggedIn = await authStore.checkAuth()
  if (!loggedIn) {
    const redirect = to.fullPath || '/'
    return { name: 'login', query: { redirect } }
  }

  return true
})

export default router
