import { createRouter, createWebHistory } from 'vue-router'
import { getToken, getUserInfo } from '@/utils/auth'

// 仅管理员可访问的页面（精确匹配，避免误伤 /manager/lablist、/manager/lab-equipment）
const ADMIN_PATHS = ['/manager/lab', '/manager/equipment', '/manager/user', '/manager/auditreservation']

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // 根路径重定向到 /manager/home
    { path: '/', redirect: '/manager/home' },
    {
      path: '/manager',
      name: 'Layout',
      component: () => import('@/layout/Layout.vue'),
      children: [
        // 子路由 path 不能以 / 开头，会被拼接为 /manager/home
        { path: 'home', name: 'Home', component: () => import('@/views/Home.vue') },
        { path: 'lab', name: 'Lab', component: () => import('@/views/Lab.vue') },
        { path: 'equipment', name: 'Equipment', component: () => import('@/views/Equipment.vue') },
        { path: 'user', name: 'User', component: () => import('@/views/User.vue') },
        { path: 'profile', name: 'Profile', component: () => import('@/views/Profile.vue') },
        { path: 'password', name: 'Password', component: () => import('@/views/Password.vue') },
        { path: 'lablist', name: 'LabList', component: () => import('@/views/LabList.vue') },
        { path: 'lab-equipment', name: 'LabEquipment', component: () => import('@/views/LabEquipment.vue') },
        { path: 'labcalendar', name: 'LabCalendar', component: () => import('@/views/LabCalendar.vue') },
        { path: 'myreservation', name: 'MyReservation', component: () => import('@/views/MyReservation.vue') },
        { path: 'auditreservation', name: 'AuditReservation', component: () => import('@/views/AuditReservation.vue') },
        { path: 'aichat', name: 'AIChat', component: () => import('@/views/AIChat.vue') },

      ]
    },
    // ✅ 正确写法：加上 () =>
    { path: '/login', name: 'Login', component: () => import('@/views/Login.vue') },
    { path: '/register', name: 'Register', component: () => import('@/views/Register.vue') },
    
    // 404 兜底（必须放在最后）

    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/NotFound.vue')
    }
  ]
})

// 注意：这里去掉了 next 参数
router.beforeEach((to, from) => {
  const token = getToken()

  // 1. 如果是去登录页或注册页，直接放行
  if (to.path === '/login' || to.path === '/register') {
    return true
  }

  // 2. 没有 token 一律去登录页
  if (!token) return '/login'

  // 3. 管理员页面校验角色（后端接口同样有校验，这里避免学生误入管理页）
  if (ADMIN_PATHS.includes(to.path)) {
    const role = getUserInfo()?.role
    return role === 'admin' ? true : '/manager/home'
  }

  return true
})
export default router