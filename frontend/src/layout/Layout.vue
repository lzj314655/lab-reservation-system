<template>
  <el-container class="layout-container">
    <!-- 顶部 Header -->
    <el-header class="layout-header">
      <!-- 左侧 Logo 区域 -->
        <div class="logo-area" @click="router.push('/manager/home')">
          <!-- 保留了你原有的本地图片 -->
          <img class="logo-img" src="@/imgs/logo.png" alt="logo" />
          <span class="logo-title">智能<em>实验室</em>预约系统</span>
        </div>

      <!-- 右侧用户信息区域 -->
      <div class="user-area">
        <!-- 通知铃铛 -->
        <el-popover placement="bottom-end" :width="360" trigger="click" popper-class="notif-popper" @show="fetchNotifList">
          <template #reference>
            <div class="bell-trigger">
              <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
                <el-icon :size="20"><Bell /></el-icon>
              </el-badge>
            </div>
          </template>
          <div class="notif-panel">
            <div class="notif-head">
              <span class="notif-title">通知</span>
              <el-button v-if="unreadCount > 0" link type="primary" size="small" @click="handleReadAll">全部已读</el-button>
            </div>
            <el-scrollbar max-height="320px">
              <div v-if="notifList.length === 0" class="notif-empty">暂无通知</div>
              <div
                v-for="item in notifList"
                :key="item.id"
                class="notif-item"
                :class="{ unread: item.is_read === 0 }"
                @click="handleNotifClick(item)"
              >
                <div class="notif-icon" :class="item.type">
                  <span v-if="item.type === 'audit_pass'">✓</span>
                  <span v-else-if="item.type === 'audit_reject'">✕</span>
                  <span v-else-if="item.type === 'reservation'">📅</span>
                  <span v-else>💡</span>
                </div>
                <div class="notif-body">
                  <div class="notif-item-title">{{ item.title }}</div>
                  <div class="notif-item-content">{{ item.content }}</div>
                  <div class="notif-item-time font-num">{{ item.create_time }}</div>
                </div>
              </div>
            </el-scrollbar>
          </div>
        </el-popover>

        <!-- 头像 -->
        <el-avatar :size="34" :src="avatarUrl" class="user-avatar">
          {{ displayName.charAt(0) }}
        </el-avatar>

        <!-- 下拉菜单 -->
        <el-dropdown @command="handleCommand" trigger="click">
          <div class="user-dropdown-trigger">
            <span class="user-name">{{ displayName }}</span>
            <el-icon class="arrow-icon"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu class="custom-dropdown">
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>个人中心
              </el-dropdown-item>
              <el-dropdown-item command="password">
                <el-icon><Lock /></el-icon>更换密码
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-container class="main-container">
      <!-- 左侧侧边栏 -->
      <el-aside width="232px" class="layout-aside">
        <div class="aside-caption">功能导航</div>
        <!-- 菜单组件：使用 router 模式，default-active 绑定当前路由 -->
        <el-menu :default-active="route.path" class="custom-menu" router>

          <el-menu-item index="/manager/home">
            <el-icon><Odometer /></el-icon>
            <span>系统首页</span>
          </el-menu-item>

          <!-- 管理员菜单 -->
          <template v-if="isAdmin">
            <el-menu-item index="/manager/lab">
              <el-icon><OfficeBuilding /></el-icon>
              <span>实验室管理</span>
            </el-menu-item>
            <el-menu-item index="/manager/equipment">
              <el-icon><Monitor /></el-icon>
              <span>设备列表管理</span>
            </el-menu-item>
            <el-menu-item index="/manager/user">
              <el-icon><UserFilled /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
            <el-menu-item index="/manager/auditreservation">
              <el-icon><Tickets /></el-icon>
              <span>预约审核管理</span>
            </el-menu-item>
          </template>

          <!-- 学生菜单 -->
          <template v-if="!isAdmin && userInfo.role === 'student'">
            <el-menu-item index="/manager/labcalendar">
              <el-icon><Calendar /></el-icon>
              <span>预约日历</span>
            </el-menu-item>
            <el-menu-item index="/manager/lablist">
              <el-icon><OfficeBuilding /></el-icon>
              <span>实验室列表</span>
            </el-menu-item>
            <el-menu-item index="/manager/myreservation">
              <el-icon><Tickets /></el-icon>
              <span>我的预约记录</span>
            </el-menu-item>
          </template>

          <!-- 公共菜单 -->
          <el-menu-item index="/manager/aichat">
            <el-icon><Service /></el-icon>
            <span>AI智能助手</span>
            <div class="menu-badge">NEW</div>
          </el-menu-item>

        </el-menu>

        <div class="aside-footer">
          <div class="aside-footer-dot"></div>
          智能实验室预约系统 v1.0
        </div>
      </el-aside>

      <!-- 右侧内容区 -->
      <el-main class="layout-main">
        <!-- 路由视图，加入了一点渐隐渐显的切换动画 -->
        <router-view v-slot="{ Component }">
          <transition name="fade-transform" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { logout } from '@/utils/auth'
import { getUserInfo } from '@/api/user'
import {
  getNotificationList,
  getUnreadCount,
  markNotificationRead,
  markAllNotificationRead
} from '@/api/notification'
// 引入所有需要的图标
import {
  ArrowDown,
  Odometer,
  OfficeBuilding,
  Monitor,
  User,
  UserFilled,
  Tickets,
  Service,
  Lock,
  SwitchButton,
  Bell,
  Calendar
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// 👇 用户信息
const userInfo = ref({
  name: '',
  username: '',
  avatar: '',
  role: ''
})

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

// 显示名
const displayName = computed(() => {
  return userInfo.value.name || userInfo.value.username || '用户'
})

// 头像完整地址
const avatarUrl = computed(() => {
  const a = userInfo.value.avatar
  if (!a) return ''
  return a.startsWith('http') ? a : API_BASE + a
})

// 👇 是否管理员
const isAdmin = computed(() => {
  const role = String(userInfo.value.role || '').toLowerCase()
  const username = String(userInfo.value.username || '').toLowerCase()
  return role === 'admin' || username === 'admin'
})

// 拉取用户信息
async function fetchUser() {
  try {
    const res = await getUserInfo()
    const data = res?.data ?? res
    userInfo.value = {
      name: data.name ?? '',
      username: data.username ?? '',
      avatar: data.avatar ?? '',
      role: data.role ?? data.roleName ?? ''
    }
  } catch (err) {
    console.warn('获取用户信息失败', err)
  }
}

// ============ 站内通知 ============
const unreadCount = ref(0)
const notifList = ref([])
let notifTimer = null

async function fetchUnread() {
  try {
    const res = await getUnreadCount()
    if (res.code === 200) unreadCount.value = res.data?.count ?? 0
  } catch (err) {
    /* 静默失败，不打扰用户 */
  }
}

async function fetchNotifList() {
  try {
    const res = await getNotificationList({ page: 1, page_size: 10 })
    if (res.code === 200) notifList.value = res.data?.list || []
  } catch (err) {
    console.warn('获取通知失败', err)
  }
}

async function handleNotifClick(item) {
  if (item.is_read === 0) {
    try {
      await markNotificationRead(item.id)
      item.is_read = 1
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch (err) {
      /* 忽略 */
    }
  }
  // 审核类通知跳转到预约记录
  if (item.type === 'audit_pass' || item.type === 'audit_reject' || item.type === 'reservation') {
    router.push('/manager/myreservation')
  }
}

async function handleReadAll() {
  try {
    await markAllNotificationRead()
    unreadCount.value = 0
    notifList.value = notifList.value.map((i) => ({ ...i, is_read: 1 }))
    ElMessage.success('已全部标记为已读')
  } catch (err) {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  fetchUser()
  fetchUnread()
  notifTimer = setInterval(fetchUnread, 60000)
  window.addEventListener('user-info-updated', fetchUser)
})
onUnmounted(() => {
  if (notifTimer) clearInterval(notifTimer)
  window.removeEventListener('user-info-updated', fetchUser)
})

// 下拉菜单点击处理
const handleCommand = (command) => {
  if (command === 'profile') {
    router.push('/manager/profile')
  } else if (command === 'password') {
    router.push('/manager/password')
  } else if (command === 'logout') {
    handleLogout()
  }
}

// 退出登录
const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗?', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(() => {
      logout()
      ElMessage.success('已安全退出')
      router.replace('/login')
    })
    .catch(() => {})
}
</script>

<style scoped>
/* ================= 整体布局 ================= */
.layout-container {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background-color: var(--lab-bg);
  background-image: radial-gradient(circle, rgba(14, 116, 144, 0.055) 1px, transparent 1px);
  background-size: 22px 22px;
}

.main-container {
  height: calc(100vh - 64px);
}

/* ================= 顶部 Header ================= */
.layout-header {
  height: 64px;
  background-color: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(12px);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  border-bottom: 1px solid var(--lab-border);
  z-index: 10;
}

.logo-area {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
  gap: 12px;
}

.logo-img {
  width: 38px;
  height: 38px;
  object-fit: contain;
  filter: drop-shadow(0 2px 6px rgba(14, 116, 144, 0.35));
}

.logo-title {
  font-size: 19px;
  font-weight: 800;
  color: var(--lab-ink);
  letter-spacing: 0.02em;
}

.logo-title em {
  font-style: normal;
  color: var(--lab-primary);
}

.user-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ============ 通知铃铛 ============ */
.bell-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  cursor: pointer;
  color: var(--lab-text-2);
  transition: background-color 0.2s, color 0.2s;
}

.bell-trigger:hover {
  background-color: #e8f3f6;
  color: var(--lab-primary);
}

.notif-panel { margin: -4px -6px; }

.notif-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid var(--lab-border);
}

.notif-title { font-weight: 700; font-size: 14.5px; color: var(--lab-text); }

.notif-empty {
  padding: 36px 0;
  text-align: center;
  color: var(--lab-text-3);
  font-size: 13px;
}

.notif-item {
  display: flex;
  gap: 10px;
  padding: 11px 14px;
  cursor: pointer;
  transition: background-color 0.15s;
}

.notif-item:hover { background-color: #f5f9fa; }
.notif-item.unread { background-color: #f0f7f9; }
.notif-item.unread:hover { background-color: #e6f1f4; }

.notif-icon {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
}
.notif-icon.audit_pass { background: #e7f7f0; color: #059669; }
.notif-icon.audit_reject { background: #fdeeee; color: #dc2626; }
.notif-icon.reservation { background: #e8f3f6; color: #0e7490; }
.notif-icon.info { background: #fdf3e3; color: #d97706; }

.notif-body { flex: 1; min-width: 0; }

.notif-item-title {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--lab-text);
}

.notif-item-content {
  font-size: 12.5px;
  color: var(--lab-text-2);
  margin: 3px 0 4px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notif-item-time { font-size: 11px; color: var(--lab-text-3); }

.user-avatar {
  background: linear-gradient(135deg, #0e7490, #22a0b8);
  color: #fff;
  font-weight: 700;
  box-shadow: 0 2px 8px rgba(14, 116, 144, 0.3);
}

.user-dropdown-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 999px;
  cursor: pointer;
  transition: background-color 0.2s;
  border: 1px solid transparent;
}

.user-dropdown-trigger:hover {
  background-color: #f2f7f9;
  border-color: var(--lab-border);
}

.user-name {
  font-size: 14px;
  color: var(--lab-text);
  font-weight: 600;
}

.arrow-icon {
  font-size: 12px;
  color: var(--lab-text-3);
  transition: transform 0.2s;
}

.user-dropdown-trigger:hover .arrow-icon {
  transform: rotate(180deg);
}

/* ================= 左侧深色侧边栏 ================= */
.layout-aside {
  background: linear-gradient(180deg, #0b1a26 0%, #0c2231 60%, #0b2736 100%);
  display: flex;
  flex-direction: column;
  padding: 14px 12px;
  overflow-y: auto;
}

.aside-caption {
  font-size: 11px;
  letter-spacing: 0.24em;
  color: rgba(157, 178, 194, 0.55);
  padding: 6px 12px 10px;
  font-weight: 600;
}

.custom-menu {
  border-right: none;
  flex: 1;
  background-color: transparent;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: #9db2c2;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.06);
  --el-menu-active-color: #ffffff;
}

/* 菜单项基础样式 */
:deep(.el-menu-item) {
  height: 46px;
  line-height: 46px;
  border-radius: 10px;
  margin-bottom: 6px;
  color: #9db2c2;
  font-size: 14.5px;
  font-weight: 500;
  transition: all 0.2s ease;
  position: relative;
}

/* 图标微调 */
:deep(.el-menu-item .el-icon) {
  font-size: 18px;
  margin-right: 12px;
  transition: transform 0.25s;
}

/* 菜单悬浮状态 */
:deep(.el-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.07) !important;
  color: #e8f1f5 !important;
}

:deep(.el-menu-item:hover .el-icon) {
  transform: scale(1.12);
}

/* 菜单选中状态：青色渐变 + 左侧光条 */
:deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(14, 116, 144, 0.55), rgba(14, 116, 144, 0.18)) !important;
  color: #ffffff !important;
  font-weight: 700;
  box-shadow: inset 0 0 0 1px rgba(94, 203, 229, 0.25), 0 4px 14px rgba(0, 0, 0, 0.25);
}

:deep(.el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 22px;
  width: 4px;
  border-radius: 0 4px 4px 0;
  background: linear-gradient(180deg, #5ecbe5, #0e7490);
  box-shadow: 0 0 12px rgba(94, 203, 229, 0.8);
}

/* 侧栏底部 */
.aside-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 12px 12px 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  font-size: 11.5px;
  color: rgba(157, 178, 194, 0.55);
  user-select: none;
}

.aside-footer-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 8px rgba(52, 211, 153, 0.8);
  animation: pulse-dot 2.4s infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

/* AI 助手特有的 NEW 标签 */
.menu-badge {
  margin-left: auto;
  background: linear-gradient(90deg, #fe6d56, #ff8e53);
  color: white;
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  box-shadow: 0 2px 8px rgba(254, 109, 86, 0.45);
}

/* ================= 右侧内容区 ================= */
.layout-main {
  padding: 22px;
  overflow-y: auto;
}

/* 路由切换动画 */
.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: all 0.25s ease;
}
.fade-transform-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.fade-transform-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>