import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { guest: true },
  },
  {
    path: '/chat',
    name: 'ChatLayout',
    component: () => import('@/views/ChatLayout.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/chat/:id',
    name: 'Chat',
    component: () => import('@/views/ChatLayout.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/faq',
    name: 'FaqManage',
    component: () => import('@/views/FaqManage.vue'),
    meta: { requiresAuth: true, requiresTechSupport: true },
  },
  {
    path: '/upload',
    name: 'DocumentUpload',
    component: () => import('@/views/DocumentUpload.vue'),
    meta: { requiresAuth: true, requiresTechSupport: true },
  },
  {
    path: '/rag-dashboard',
    name: 'RagDashboard',
    component: () => import('@/views/RagDashboard.vue'),
    meta: { requiresAuth: true, requiresTechSupport: true },
  },
  {
    path: '/tech-dashboard',
    name: 'TechDashboard',
    component: () => import('@/views/TechDashboard.vue'),
    meta: { requiresAuth: true, requiresTechSupport: true },
  },
  {
    path: '/user-dashboard',
    name: 'UserDashboard',
    component: () => import('@/views/UserDashboard.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/chat',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // Guest-only pages (login/register) — redirect based on role
  if (to.meta.guest && authStore.isLoggedIn) {
    return next(authStore.isTechSupport ? '/tech-dashboard' : '/chat')
  }

  // Auth-required pages
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return next('/login')
  }

  // Tech-support landing: redirect from bare /chat to dashboard
  if (authStore.isTechSupport && to.path === '/chat' && !to.params.id) {
    return next('/tech-dashboard')
  }

  // Tech-support-only pages
  if (to.meta.requiresTechSupport && !authStore.isTechSupport) {
    import('element-plus').then(({ ElMessage }) => {
      ElMessage.warning('权限不足，仅技术支持人员可访问')
    })
    return next('/chat')
  }

  next()
})

export default router
