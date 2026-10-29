<template>
  <div class="auth-shell">
    <!-- 左侧品牌区 -->
    <div class="auth-brand">
      <div class="brand-inner">
        <div class="brand-logo">
          <img src="@/imgs/logo.png" alt="logo" />
          <div class="brand-name">智能实验室预约系统</div>
        </div>
        <h1 class="brand-headline">让每一间实验室<br />都被高效使用</h1>
        <p class="brand-sub">预约 · 审核 · 设备管理 · AI 智能助手，一站式完成</p>

        <ul class="brand-features">
          <li>
            <span class="feature-icon">📅</span>
            <div>
              <b>在线预约</b>
              <i>按日历时段预约实验室与设备</i>
            </div>
          </li>
          <li>
            <span class="feature-icon">🔬</span>
            <div>
              <b>设备台账</b>
              <i>设备状态、规格、所属实验室一目了然</i>
            </div>
          </li>
          <li>
            <span class="feature-icon">🤖</span>
            <div>
              <b>AI 助手</b>
              <i>一句话查规则、查空闲、完成预约</i>
            </div>
          </li>
        </ul>
      </div>

      <!-- 装饰元素 -->
      <div class="deco deco-grid"></div>
      <div class="deco deco-circle c1"></div>
      <div class="deco deco-circle c2"></div>
      <div class="deco deco-molecule">
        <svg viewBox="0 0 200 200" fill="none">
          <line x1="60" y1="60" x2="140" y2="90" stroke="rgba(94,203,229,.4)" stroke-width="1.5" />
          <line x1="140" y1="90" x2="100" y2="150" stroke="rgba(94,203,229,.4)" stroke-width="1.5" />
          <line x1="60" y1="60" x2="100" y2="150" stroke="rgba(94,203,229,.25)" stroke-width="1.5" />
          <circle cx="60" cy="60" r="14" fill="rgba(94,203,229,.16)" stroke="rgba(94,203,229,.7)" stroke-width="1.5" />
          <circle cx="140" cy="90" r="9" fill="rgba(245,158,11,.14)" stroke="rgba(245,158,11,.65)" stroke-width="1.5" />
          <circle cx="100" cy="150" r="12" fill="rgba(94,203,229,.12)" stroke="rgba(94,203,229,.5)" stroke-width="1.5" />
        </svg>
      </div>
    </div>

    <!-- 右侧表单区 -->
    <div class="auth-form-side">
      <div class="auth-card fade-up">
        <div class="auth-title">欢迎回来 👋</div>
        <div class="auth-subtitle">登录你的账号，开始预约</div>

        <el-form ref="loginFormRef" :model="loginForm" :rules="rules" class="login-form" size="large">
          <el-form-item prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="请输入账号"
              :prefix-icon="User"
              size="large"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              size="large"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              class="login-button"
              :loading="loading"
              @click="handleLogin"
            >
              登 录
            </el-button>
          </el-form-item>
          <div class="auth-footer">
            还没有账号？<el-link type="primary" @click="$router.push('/register')">立即注册</el-link>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { loginApi } from '@/api/auth'
import { setToken, setUserInfo } from '@/utils/auth'

const router = useRouter()
const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = reactive({
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
})

const handleLogin = () => {
  if (!loginFormRef.value) return

  loginFormRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true

    try {
      const res = await loginApi({
        username: loginForm.username,
        password: loginForm.password
      })

      if (res.code === 200 || res.code === 0) {
        ElMessage.success('登录成功')

        if (res.data && res.data.token) {
          setToken(res.data.token)
          if (res.data.user) {
            setUserInfo(res.data.user)
          }
        }

        const role = res.data?.user?.role || res.data?.role
        if (role === 'manager') {
          router.push('/manager/home')
        } else if (role === 'student') {
          router.push('/')
        } else {
          router.push('/manager/home')
        }

      } else {
        ElMessage.error(res.message || res.msg || '账号或密码错误')
      }
    } catch (error) {
      const errorMsg = error.response?.data?.message || error.message || '登录失败，请稍后再试'
      ElMessage.error(errorMsg)
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.auth-shell {
  display: flex;
  min-height: 100vh;
}

/* ============ 左侧品牌区 ============ */
.auth-brand {
  position: relative;
  flex: 0 0 46%;
  background:
    radial-gradient(1200px 600px at -10% -20%, rgba(14, 116, 144, 0.55), transparent 55%),
    radial-gradient(800px 500px at 110% 110%, rgba(34, 160, 184, 0.4), transparent 60%),
    linear-gradient(160deg, #0b1a26 0%, #0c2736 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: #e8f1f5;
}

.brand-inner {
  position: relative;
  z-index: 2;
  width: min(420px, 82%);
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 44px;
}

.brand-logo img {
  width: 44px;
  height: 44px;
  filter: drop-shadow(0 4px 12px rgba(94, 203, 229, 0.4));
}

.brand-name {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: rgba(232, 241, 245, 0.92);
}

.brand-headline {
  font-size: 34px;
  font-weight: 800;
  line-height: 1.35;
  letter-spacing: 0.01em;
  margin-bottom: 14px;
}

.brand-sub {
  font-size: 14.5px;
  color: rgba(157, 178, 194, 0.85);
  margin-bottom: 40px;
  letter-spacing: 0.02em;
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.brand-features li {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(4px);
  transition: transform 0.25s ease, background-color 0.25s ease;
}

.brand-features li:hover {
  transform: translateX(4px);
  background: rgba(255, 255, 255, 0.08);
}

.feature-icon {
  font-size: 22px;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: rgba(94, 203, 229, 0.12);
  border: 1px solid rgba(94, 203, 229, 0.25);
}

.brand-features b {
  display: block;
  font-size: 14.5px;
  font-weight: 700;
  margin-bottom: 2px;
}

.brand-features i {
  font-style: normal;
  font-size: 12.5px;
  color: rgba(157, 178, 194, 0.9);
}

/* 装饰 */
.deco {
  position: absolute;
  pointer-events: none;
}

.deco-grid {
  inset: 0;
  background-image:
    linear-gradient(rgba(94, 203, 229, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(94, 203, 229, 0.05) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 78%);
}

.deco-circle {
  border-radius: 50%;
  border: 1px solid rgba(94, 203, 229, 0.16);
}

.deco-circle.c1 {
  width: 420px;
  height: 420px;
  top: -140px;
  right: -120px;
  animation: float-slow 14s ease-in-out infinite;
}

.deco-circle.c2 {
  width: 260px;
  height: 260px;
  bottom: -80px;
  left: -60px;
  border-color: rgba(245, 158, 11, 0.14);
  animation: float-slow 11s ease-in-out infinite reverse;
}

.deco-molecule {
  right: 8%;
  bottom: 12%;
  width: 190px;
  height: 190px;
  opacity: 0.9;
  animation: float-slow 9s ease-in-out infinite;
}

@keyframes float-slow {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-16px) rotate(2deg); }
}

/* ============ 右侧表单区 ============ */
.auth-form-side {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  background-color: var(--lab-bg);
  background-image: radial-gradient(circle, rgba(14, 116, 144, 0.05) 1px, transparent 1px);
  background-size: 22px 22px;
}

.auth-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border: 1px solid var(--lab-border);
  border-radius: 20px;
  padding: 38px 36px 30px;
  box-shadow: var(--lab-shadow-lg);
}

.auth-title {
  font-size: 25px;
  font-weight: 800;
  color: var(--lab-ink);
  margin-bottom: 8px;
}

.auth-subtitle {
  font-size: 13.5px;
  color: var(--lab-text-3);
  margin-bottom: 28px;
}

.login-form {
  margin-top: 4px;
}

.login-button {
  width: 100%;
  margin-top: 6px;
  font-size: 15.5px;
  height: 44px;
  letter-spacing: 6px;
  border-radius: 10px;
  background: linear-gradient(135deg, #0e7490, #159bb5);
}

.login-button:hover {
  background: linear-gradient(135deg, #0b5c74, #0e7490);
}

.auth-footer {
  margin-top: 6px;
  text-align: center;
  font-size: 13.5px;
  color: var(--lab-text-2);
}

/* 窄屏隐藏品牌区 */
@media (max-width: 900px) {
  .auth-brand {
    display: none;
  }
}
</style>
