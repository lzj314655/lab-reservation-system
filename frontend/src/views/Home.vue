<template>
  <div class="home-container">
    <!-- 欢迎横幅：深青渐变 -->
    <div class="welcome-banner fade-up">
      <div class="banner-content">
        <div class="banner-eyebrow">WELCOME BACK</div>
        <h1 class="greeting">{{ greeting }}，{{ username }} 👋</h1>
        <p class="subtitle">欢迎使用智能实验室预约系统，愿今天的工作顺利高效</p>
        <div class="time-info">
          <el-icon><Calendar /></el-icon>
          <span>{{ currentDate }}</span>
        </div>
      </div>
      <!-- 装饰元素 -->
      <div class="banner-decoration">
        <div class="circle circle-1"></div>
        <div class="circle circle-2"></div>
        <div class="circle circle-3"></div>
        <svg class="banner-molecule" viewBox="0 0 200 200" fill="none">
          <line x1="60" y1="60" x2="140" y2="90" stroke="rgba(94,203,229,.35)" stroke-width="1.5" />
          <line x1="140" y1="90" x2="100" y2="150" stroke="rgba(94,203,229,.35)" stroke-width="1.5" />
          <line x1="60" y1="60" x2="100" y2="150" stroke="rgba(94,203,229,.2)" stroke-width="1.5" />
          <circle cx="60" cy="60" r="14" fill="rgba(94,203,229,.14)" stroke="rgba(94,203,229,.6)" stroke-width="1.5" />
          <circle cx="140" cy="90" r="9" fill="rgba(245,158,11,.12)" stroke="rgba(245,158,11,.55)" stroke-width="1.5" />
          <circle cx="100" cy="150" r="12" fill="rgba(94,203,229,.1)" stroke="rgba(94,203,229,.45)" stroke-width="1.5" />
        </svg>
      </div>
    </div>

    <!-- 数据统计卡片（真实数据） -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6" v-for="(item, index) in statCards" :key="item.label">
        <el-card shadow="never" class="stat-card fade-up" :class="'fade-up-' + (index + 1)">
          <div class="stat-content">
            <div class="stat-info">
              <div class="stat-label">{{ item.label }}</div>
              <div class="stat-value font-num">
                <span v-if="!loadingStats">{{ item.value }}</span>
                <el-icon v-else class="is-loading"><Loading /></el-icon>
                <span class="unit">{{ item.unit }}</span>
              </div>
            </div>
            <div class="stat-icon-wrapper" :style="{ background: item.tileBg }">
              <el-icon :size="26" :style="{ color: item.color }"><component :is="item.icon" /></el-icon>
            </div>
          </div>
          <div class="stat-footer">
            <span v-if="item.extra" class="trend" :class="item.extraClass || 'flat'">{{ item.extra }}</span>
            <span class="desc">{{ item.desc }}</span>
          </div>
          <div class="card-line" :style="{ background: item.lineBg }"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="16">
        <el-card shadow="never" class="chart-card fade-up fade-up-2">
          <div class="chart-title">近 30 天预约趋势</div>
          <div ref="trendChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="chart-card fade-up fade-up-3">
          <div class="chart-title">{{ isAdmin ? '实验室预约量排行' : '我的预约状态分布' }}</div>
          <div ref="sideChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷操作区 -->
    <div class="quick-actions">
      <div class="section-title">快捷操作</div>
      <el-row :gutter="20">
        <el-col :span="8" v-for="(action, index) in quickActions" :key="index">
          <div class="action-card fade-up" :class="'fade-up-' + (index + 1)" @click="router.push(action.path)">
            <div class="action-icon" :style="{ background: action.tileBg, color: action.color }">
              <el-icon :size="24"><component :is="action.icon" /></el-icon>
            </div>
            <div class="action-text">
              <h4>{{ action.title }}</h4>
              <p>{{ action.desc }}</p>
            </div>
            <el-icon class="action-arrow"><ArrowRight /></el-icon>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Calendar, ArrowRight, Monitor, AlarmClock, Tickets, Bell, Calendar as CalendarIcon } from '@element-plus/icons-vue'
import { getUserInfo } from '@/utils/auth'
import { getStatsOverview, getStatsTrend, getLabUsage, getMyReservationStatus } from '@/api/stats'

const router = useRouter()
const username = ref(getUserInfo()?.name || getUserInfo()?.username || '用户')
const isAdmin = computed(() => getUserInfo()?.role === 'admin')

// 时间问候逻辑
const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '凌晨好'
  if (hour < 9) return '早上好'
  if (hour < 12) return '上午好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const currentDate = computed(() => {
  const date = new Date()
  const year = date.getFullYear()
  const month = date.getMonth() + 1
  const day = date.getDate()
  const days = ['日', '一', '二', '三', '四', '五', '六']
  return `${year}年${month}月${day}日 星期${days[date.getDay()]}`
})

// ============ 真实统计 ============
const loadingStats = ref(true)
const overview = ref({})
const statCards = ref([])

function buildStatCards(d) {
  const common = {
    openLabs: {
      label: '可用实验室', value: d.open_labs ?? 0, unit: '间', icon: 'Monitor',
      color: '#0e7490', tileBg: 'linear-gradient(135deg,#e6f4f8,#f2fafc)',
      lineBg: 'linear-gradient(90deg,#0e7490,#22a0b8)', desc: '当前开放中'
    },
    unread: {
      label: '未读通知', value: d.unread ?? 0, unit: '条', icon: 'Bell',
      color: '#dc2626', tileBg: 'linear-gradient(135deg,#fdeeee,#fff7f7)',
      lineBg: 'linear-gradient(90deg,#ef4444,#f87171)', desc: '站内消息'
    }
  }
  const pending = {
    label: '待审核预约', value: d.pending ?? 0, unit: '条', icon: 'AlarmClock',
    color: '#d97706', tileBg: 'linear-gradient(135deg,#fdf3e3,#fef9f0)',
    lineBg: 'linear-gradient(90deg,#f59e0b,#fbbf24)',
    desc: isAdmin.value ? '全系统待处理' : '我的待审核'
  }
  if (isAdmin.value) {
    return [
      common.openLabs,
      pending,
      {
        label: '本周新增预约', value: d.week_count ?? 0, unit: '条', icon: 'Tickets',
        color: '#059669', tileBg: 'linear-gradient(135deg,#e7f7f0,#f2fbf7)',
        lineBg: 'linear-gradient(90deg,#10b981,#34d399)', desc: '本周一至今',
        extra: d.pass_rate != null ? `审核通过率 ${d.pass_rate}%` : '',
        extraClass: 'up'
      },
      common.unread
    ]
  }
  return [
    common.openLabs,
    pending,
    {
      label: '我的预约总数', value: d.total ?? 0, unit: '次', icon: 'Tickets',
      color: '#059669', tileBg: 'linear-gradient(135deg,#e7f7f0,#f2fbf7)',
      lineBg: 'linear-gradient(90deg,#10b981,#34d399)', desc: '全部记录'
    },
    common.unread
  ]
}

// ============ 图表 ============
const trendChartRef = ref(null)
const sideChartRef = ref(null)
let trendChart = null
let sideChart = null

function renderTrendChart(data) {
  if (!trendChartRef.value) return
  trendChart = echarts.init(trendChartRef.value)
  trendChart.setOption({
    grid: { left: 40, right: 16, top: 24, bottom: 28 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: data.map(i => i.date.slice(5)),
      axisLine: { lineStyle: { color: '#d5dee6' } },
      axisLabel: { color: '#8b98a8', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#eef2f5' } },
      axisLabel: { color: '#8b98a8', fontSize: 11 }
    },
    series: [{
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      data: data.map(i => i.count),
      lineStyle: { width: 3, color: '#0e7490' },
      itemStyle: { color: '#0e7490', borderColor: '#fff', borderWidth: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(14,116,144,0.22)' },
          { offset: 1, color: 'rgba(14,116,144,0.02)' }
        ])
      }
    }]
  })
}

function renderSideChartAdmin(data) {
  if (!sideChartRef.value) return
  sideChart = echarts.init(sideChartRef.value)
  sideChart.setOption({
    grid: { left: 4, right: 30, top: 10, bottom: 8, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#eef2f5' } }, axisLabel: { color: '#8b98a8', fontSize: 11 } },
    yAxis: {
      type: 'category',
      data: [...data].reverse().map(i => i.lab_name),
      axisLabel: { color: '#5b6b7c', fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    series: [{
      type: 'bar',
      barWidth: 12,
      itemStyle: { borderRadius: [0, 6, 6, 0], color: '#159bb5' },
      data: [...data].reverse().map(i => i.count)
    }]
  })
}

function renderSideChartStudent(data) {
  if (!sideChartRef.value) return
  sideChart = echarts.init(sideChartRef.value)
  const palette = { '待审核': '#f59e0b', '已通过': '#10b981', '已拒绝': '#ef4444', '已取消': '#8b98a8' }
  sideChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 次 ({d}%)' },
    legend: { bottom: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: '#5b6b7c', fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '44%'],
      label: { show: false },
      data: data.map(i => ({ ...i, itemStyle: { color: palette[i.name] || '#8b98a8' } }))
    }]
  })
}

const handleResize = () => {
  trendChart?.resize()
  sideChart?.resize()
}

// 快捷操作配置
const quickActions = ref([
  { title: '预约实验室', desc: '按日历时段预约，实时查看占用', icon: 'Calendar', color: '#0e7490', tileBg: 'linear-gradient(135deg,#dff0f5,#eef8fa)', path: '/manager/labcalendar' },
  { title: '实验室列表', desc: '浏览实验室与设备详情', icon: 'OfficeBuilding', color: '#7c3aed', tileBg: 'linear-gradient(135deg,#f1ecfd,#f8f5fe)', path: '/manager/lablist' },
  { title: '咨询 AI 助手', desc: '一句话查规则、查空闲、完成预约', icon: 'Service', color: '#e2553a', tileBg: 'linear-gradient(135deg,#feefec,#fff6f4)', path: '/manager/aichat' }
])

onMounted(async () => {
  window.addEventListener('resize', handleResize)

  // 统计卡 + 图表
  try {
    const [ovRes, trendRes] = await Promise.all([
      getStatsOverview(),
      getStatsTrend(30)
    ])
    if (ovRes.code === 200) {
      overview.value = ovRes.data
      statCards.value = buildStatCards(ovRes.data)
    }
    await nextTick()
    if (trendRes.code === 200) renderTrendChart(trendRes.data || [])
    if (isAdmin.value) {
      const res = await getLabUsage(8)
      if (res.code === 200) renderSideChartAdmin(res.data || [])
    } else {
      const res = await getMyReservationStatus()
      if (res.code === 200) renderSideChartStudent(res.data || [])
    }
  } catch (e) {
    console.error('统计加载失败', e)
  } finally {
    loadingStats.value = false
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  sideChart?.dispose()
})
</script>

<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* -------- 欢迎横幅 -------- */
.welcome-banner {
  position: relative;
  background:
    radial-gradient(900px 400px at 88% -40%, rgba(34, 160, 184, 0.45), transparent 60%),
    linear-gradient(135deg, #0b1a26 0%, #0e2c3d 55%, #0e7490 130%);
  border-radius: 20px;
  padding: 38px 42px;
  overflow: hidden;
  box-shadow: 0 14px 34px rgba(8, 63, 82, 0.28);
  color: #e8f1f5;
}

.banner-content { position: relative; z-index: 2; }

.banner-eyebrow {
  font-size: 11px;
  letter-spacing: 0.34em;
  font-weight: 700;
  color: rgba(94, 203, 229, 0.85);
  margin-bottom: 10px;
}

.greeting {
  margin: 0 0 10px 0;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0.01em;
}

.subtitle {
  margin: 0 0 20px 0;
  font-size: 14px;
  color: rgba(202, 221, 231, 0.85);
}

.time-info {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  padding: 7px 16px;
  border-radius: 999px;
  font-size: 13px;
  color: #d7e7ed;
  backdrop-filter: blur(4px);
}

.banner-decoration .circle {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(94, 203, 229, 0.2);
}

.circle-1 { width: 260px; height: 260px; top: -90px; right: 60px; }
.circle-2 { width: 140px; height: 140px; bottom: -50px; right: 230px; border-color: rgba(245, 158, 11, 0.22); }
.circle-3 { width: 70px; height: 70px; top: 46px; right: 300px; background: rgba(94, 203, 229, 0.08); }

.banner-molecule {
  position: absolute;
  right: 90px;
  bottom: -30px;
  width: 180px;
  height: 180px;
  opacity: 0.8;
}

/* -------- 数据统计卡片 -------- */
.stat-row { margin-bottom: 2px; }

.stat-card {
  border-radius: 16px;
  position: relative;
  overflow: hidden;
  cursor: default;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--lab-shadow-lg);
}

:deep(.el-card__body) { padding: 22px; }

.stat-content { display: flex; justify-content: space-between; align-items: center; }

.stat-label { font-size: 13px; color: var(--lab-text-3); margin-bottom: 10px; font-weight: 500; }

.stat-value {
  font-size: 30px;
  font-weight: 800;
  color: var(--lab-ink);
  line-height: 1;
  display: flex;
  align-items: center;
  gap: 2px;
}

.stat-value .unit { font-size: 13px; color: var(--lab-text-3); font-weight: 500; margin-left: 4px; }

.stat-icon-wrapper {
  width: 54px;
  height: 54px;
  border-radius: 14px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.stat-footer { margin-top: 16px; font-size: 12.5px; display: flex; align-items: center; gap: 8px; }

.trend { font-weight: 700; padding: 2px 8px; border-radius: 999px; }
.trend.up { color: #0e7490; background: #e8f3f6; }
.trend.flat { color: var(--lab-text-3); background: #f1f4f7; }

.desc { color: var(--lab-text-3); }

.card-line { position: absolute; bottom: 0; left: 0; width: 100%; height: 3px; }

/* -------- 图表区 -------- */
.chart-row { margin-top: 18px; }

.chart-card { border-radius: 16px; }

.chart-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--lab-text);
  margin-bottom: 12px;
  padding-left: 12px;
  position: relative;
}

.chart-title::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(180deg, var(--lab-primary), var(--lab-amber));
}

.chart-box { height: 280px; }

/* -------- 快捷操作区 -------- */
.section-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--lab-text);
  margin: 22px 0 14px;
  position: relative;
  padding-left: 14px;
}

.section-title::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 16px;
  border-radius: 4px;
  background: linear-gradient(180deg, var(--lab-primary), var(--lab-amber));
}

.action-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 20px 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: all 0.22s ease;
  border: 1px solid var(--lab-border);
  box-shadow: var(--lab-shadow-sm);
}

.action-card:hover {
  transform: translateY(-3px);
  border-color: rgba(14, 116, 144, 0.4);
  box-shadow: 0 10px 26px rgba(14, 116, 144, 0.14);
}

.action-card:hover .action-arrow { transform: translateX(5px); color: var(--lab-primary); }

.action-icon {
  width: 48px;
  height: 48px;
  border-radius: 13px;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-shrink: 0;
}

.action-text { flex: 1; }

.action-text h4 { margin: 0 0 5px 0; font-size: 15.5px; color: var(--lab-text); font-weight: 700; }
.action-text p { margin: 0; font-size: 12.5px; color: var(--lab-text-3); }

.action-arrow { color: var(--lab-text-3); font-size: 16px; transition: all 0.22s ease; }
</style>
