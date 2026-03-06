import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import routesConfig from './routes.json'

const routes = [
  {
    path: '/',
    redirect: routesConfig.routes.login.path
  },
  {
    path: routesConfig.routes.login.path,
    name: routesConfig.routes.login.name,
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: routesConfig.routes.login.requiresAuth }
  },
  {
    path: routesConfig.routes.chat.path,
    name: routesConfig.routes.chat.name,
    component: () => import('@/views/ChatView.vue'),
    meta: { requiresAuth: routesConfig.routes.chat.requiresAuth }
  },
  {
    path: routesConfig.routes.manager.path,
    name: routesConfig.routes.manager.name,
    component: () => import('@/views/ManagerView.vue'),
    meta: { requiresAuth: routesConfig.routes.manager.requiresAuth }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: routesConfig.routes.chat.path
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: routesConfig.routes.login.name })
  } else if (to.name === routesConfig.routes.login.name && authStore.isAuthenticated) {
    next({ name: routesConfig.routes.chat.name })
  } else {
    next()
  }
})

export default router
