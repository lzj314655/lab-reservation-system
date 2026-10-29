<template>
  <div class="calendar-container">
    <!-- 顶部工具栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <div class="page-title">预约日历</div>
          <el-select
            v-model="selectedLabId"
            placeholder="选择实验室"
            style="width: 220px"
            @change="handleLabChange"
          >
            <el-option
              v-for="item in labOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </div>

        <div class="week-nav">
          <el-button :icon="ArrowLeft" circle @click="changeWeek(-1)" />
          <div class="week-range font-num">{{ weekRangeText }}</div>
          <el-button :icon="ArrowRight" circle @click="changeWeek(1)" :disabled="!canGoNext" />
          <el-button size="small" class="today-btn" @click="goToday">回到本周</el-button>
        </div>

        <div class="legend">
          <span class="legend-item"><span class="lg approved"></span>已通过</span>
          <span class="legend-item"><span class="lg pending"></span>待审核</span>
          <span class="legend-item"><span class="lg closed"></span>非开放时间</span>
        </div>
      </div>
      <div v-if="currentLab && currentLab.status !== 1" class="lab-closed-tip">
        <el-alert title="该实验室当前已关闭，仅可查看占用情况，无法预约" type="warning" :closable="false" />
      </div>
    </el-card>

    <!-- 周视图网格 -->
    <el-card shadow="never" class="grid-card" v-loading="loading">
      <div class="week-grid">
        <!-- 左侧时间轴 -->
        <div class="time-axis">
          <div class="axis-head"></div>
          <div class="axis-body">
            <div v-for="i in slotCount" :key="i" class="axis-cell font-num">
              <template v-if="(i - 1) % 2 === 0">{{ axisTime(i - 1) }}</template>
            </div>
          </div>
        </div>

        <!-- 每天一列 -->
        <div v-for="day in weekDays" :key="day.date" class="day-col" :class="{ today: day.isToday, past: day.isPast }">
          <div class="day-head">
            <div class="day-name">周{{ day.cn }}</div>
            <div class="day-date font-num">{{ day.label }}</div>
          </div>
          <div class="day-body">
            <!-- 可点击的空时段 -->
            <div
              v-for="i in slotCount"
              :key="i"
              class="slot-cell"
              @click="handleSlotClick(day, i - 1)"
            ></div>

            <!-- 非开放时间遮罩 -->
            <div v-if="shadeTop > 0" class="closed-shade" :style="{ height: shadeTop + 'px', top: 0 }"></div>
            <div v-if="shadeBottom > 0" class="closed-shade" :style="{ height: shadeBottom + 'px', bottom: 0 }"></div>

            <!-- 预约块 -->
            <div
              v-for="block in (blocksByDate[day.date] || [])"
              :key="block.id"
              class="reserve-block"
              :class="block.status === 1 ? 'approved' : 'pending'"
              :style="blockStyle(block)"
              @click.stop="showBlockInfo(block)"
            >
              <div class="block-time font-num">{{ block.start_time }}~{{ block.end_time }}</div>
              <div class="block-name">{{ blockLabel(block) }}</div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 预约弹窗 -->
    <ReserveDialog
      v-model="dialogVisible"
      :lab-id="selectedLabId"
      :lab-name="currentLab?.name"
      :preset-date="preset.date"
      :preset-start="preset.start"
      :preset-end="preset.end"
      @success="fetchCalendar"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { getlabList } from '@/api/lab'
import { getLabCalendarApi } from '@/api/reservation'
import ReserveDialog from '@/components/ReserveDialog.vue'

const route = useRoute()

// 时间轴：08:00 ~ 22:00，每格 30 分钟
const START_HOUR = 8
const END_HOUR = 22
const SLOT_MIN = 30
const SLOT_H = 34
const slotCount = ((END_HOUR - START_HOUR) * 60) / SLOT_MIN

const loading = ref(false)
const labOptions = ref([])
const selectedLabId = ref(null)
const currentLab = ref(null)
const reservations = ref([])

// 本周一为锚点
function mondayOf(d) {
  const date = new Date(d)
  const day = date.getDay()
  date.setDate(date.getDate() - (day === 0 ? 6 : day - 1))
  date.setHours(0, 0, 0, 0)
  return date
}
const weekAnchor = ref(mondayOf(new Date()))

function fmt(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

const weekDays = computed(() => {
  const names = ['一', '二', '三', '四', '五', '六', '日']
  const today = fmt(new Date())
  const arr = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(weekAnchor.value)
    d.setDate(d.getDate() + i)
    const ds = fmt(d)
    arr.push({
      date: ds,
      label: `${d.getMonth() + 1}/${d.getDate()}`,
      cn: names[i],
      isToday: ds === today,
      isPast: ds < today
    })
  }
  return arr
})

const weekRangeText = computed(() => {
  const first = weekDays.value[0]
  const last = weekDays.value[6]
  return `${first.date} ~ ${last.date}`
})

// 不能翻到未来的第二周以外（允许看未来 1 周）
const canGoNext = computed(() => {
  const next = new Date(weekAnchor.value)
  next.setDate(next.getDate() + 7)
  const limit = mondayOf(new Date())
  limit.setDate(limit.getDate() + 14)
  return next <= limit
})

function changeWeek(dir) {
  const d = new Date(weekAnchor.value)
  d.setDate(d.getDate() + dir * 7)
  weekAnchor.value = d
  fetchCalendar()
}

function goToday() {
  weekAnchor.value = mondayOf(new Date())
  fetchCalendar()
}

function axisTime(slotIndex) {
  const m = START_HOUR * 60 + slotIndex * SLOT_MIN
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
}

function toMinutes(t) {
  const [h, m] = String(t).split(':').map(Number)
  return h * 60 + (m || 0)
}

// 实验室开放时间之外的遮罩高度
const shadeTop = computed(() => {
  const open = currentLab.value?.open_time
  if (!open) return 0
  const mins = Math.max(0, toMinutes(open) - START_HOUR * 60)
  return (mins / SLOT_MIN) * SLOT_H
})
const shadeBottom = computed(() => {
  const close = currentLab.value?.close_time
  if (!close) return 0
  const mins = Math.max(0, END_HOUR * 60 - toMinutes(close))
  return (mins / SLOT_MIN) * SLOT_H
})

const blocksByDate = computed(() => {
  const map = {}
  for (const r of reservations.value) {
    if (toMinutes(r.end_time) <= START_HOUR * 60 || toMinutes(r.start_time) >= END_HOUR * 60) continue
    ;(map[r.date] = map[r.date] || []).push(r)
  }
  return map
})

function blockStyle(block) {
  const top = ((toMinutes(block.start_time) - START_HOUR * 60) / SLOT_MIN) * SLOT_H
  const height = Math.max(
    ((toMinutes(block.end_time) - toMinutes(block.start_time)) / SLOT_MIN) * SLOT_H - 4,
    28
  )
  return { top: top + 2 + 'px', height: height + 'px' }
}

function blockLabel(block) {
  if (block.type === '设备') return block.equipment_name || '设备预约'
  return '实验室预约'
}

function showBlockInfo(block) {
  ElMessageBox.alert(
    `时间：${block.date} ${block.start_time}~${block.end_time}<br/>类型：${block.type}${
      block.equipment_name ? '（' + block.equipment_name + '）' : ''
    }<br/>预约人：${block.user_name || '-'}<br/>状态：${block.status === 1 ? '已通过' : '待审核'}`,
    '预约详情',
    { dangerouslyUseHTMLString: true, confirmButtonText: '知道了' }
  ).catch(() => {})
}

// ============ 预约交互 ============
const dialogVisible = ref(false)
const preset = reactive({ date: '', start: '', end: '' })

function handleSlotClick(day, slotIndex) {
  if (day.isPast) {
    ElMessage.warning('不能预约过去的时段')
    return
  }
  const todayStr = fmt(new Date())
  if (day.date === todayStr) {
    const now = new Date()
    const slotStart = START_HOUR * 60 + slotIndex * SLOT_MIN
    if (slotStart <= now.getHours() * 60 + now.getMinutes()) {
      ElMessage.warning('该时段已开始，请选择后面的时间')
      return
    }
  }
  if (currentLab.value && currentLab.value.status !== 1) {
    ElMessage.warning('该实验室已关闭，无法预约')
    return
  }
  const startMin = START_HOUR * 60 + slotIndex * SLOT_MIN
  const endMin = Math.min(startMin + 60, END_HOUR * 60)
  const toStr = (m) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
  preset.date = day.date
  preset.start = toStr(startMin)
  preset.end = toStr(endMin)
  dialogVisible.value = true
}

// ============ 数据加载 ============
async function fetchLabOptions() {
  try {
    const res = await getlabList({ page: 1, page_size: 100 })
    if (res.code === 200) {
      labOptions.value = res.data.list || []
      const fromQuery = Number(route.query.lab_id)
      selectedLabId.value =
        labOptions.value.find((i) => i.id === fromQuery)?.id || labOptions.value[0]?.id || null
      currentLab.value = labOptions.value.find((i) => i.id === selectedLabId.value) || null
    }
  } catch (e) {
    console.error('获取实验室列表失败', e)
  }
}

function handleLabChange(id) {
  currentLab.value = labOptions.value.find((i) => i.id === id) || null
  fetchCalendar()
}

async function fetchCalendar() {
  if (!selectedLabId.value) return
  loading.value = true
  try {
    const res = await getLabCalendarApi({
      lab_id: selectedLabId.value,
      start_date: weekDays.value[0].date,
      end_date: weekDays.value[6].date
    })
    if (res.code === 200) {
      reservations.value = res.data || []
    }
  } catch (e) {
    console.error('获取日历数据失败', e)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await fetchLabOptions()
  fetchCalendar()
})
</script>

<style scoped>
.calendar-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar-card { border-radius: 16px; }
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.toolbar-left { display: flex; align-items: center; gap: 14px; }
.page-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--lab-text);
  position: relative;
  padding-left: 14px;
}
.page-title::before {
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

.week-nav { display: flex; align-items: center; gap: 10px; }
.week-range { font-size: 14px; font-weight: 600; color: var(--lab-text-2); min-width: 200px; text-align: center; }
.today-btn { border-radius: 999px; }

.legend { display: flex; align-items: center; gap: 14px; font-size: 12.5px; color: var(--lab-text-2); }
.legend-item { display: flex; align-items: center; gap: 6px; }
.lg { width: 14px; height: 14px; border-radius: 4px; }
.lg.approved { background: linear-gradient(135deg, #0e7490, #22a0b8); }
.lg.pending { background: #fdf3e3; border: 1.5px dashed #f59e0b; }
.lg.closed { background: repeating-linear-gradient(45deg, #eef2f5 0 4px, #f6f8fa 4px 8px); border: 1px solid var(--lab-border); }

.lab-closed-tip { margin-top: 12px; }

/* ============ 网格 ============ */
.grid-card { border-radius: 16px; }
.grid-card :deep(.el-card__body) { padding: 16px; }

.week-grid { display: flex; overflow-x: auto; }

.time-axis { flex: 0 0 56px; }
.axis-head { height: 54px; }
.axis-cell { height: 34px; font-size: 11px; color: var(--lab-text-3); transform: translateY(-6px); text-align: right; padding-right: 8px; }

.day-col { flex: 1; min-width: 118px; border-left: 1px solid var(--lab-border); }
.day-col.today .day-head { background: linear-gradient(135deg, #0e7490, #159bb5); color: #fff; }
.day-col.today .day-name, .day-col.today .day-date { color: #fff; }
.day-col.past .day-body { opacity: 0.55; }

.day-head {
  height: 54px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  background: #f7fafb;
  border-radius: 10px 10px 0 0;
}
.day-name { font-size: 12.5px; color: var(--lab-text-2); font-weight: 600; }
.day-date { font-size: 13px; color: var(--lab-text); font-weight: 700; }

.day-body { position: relative; height: 952px; }

.slot-cell {
  height: 34px;
  border-top: 1px dashed #eef2f5;
  cursor: pointer;
  transition: background-color 0.12s;
}
.slot-cell:hover { background-color: rgba(14, 116, 144, 0.07); }

.closed-shade {
  position: absolute;
  left: 0; right: 0;
  background: repeating-linear-gradient(45deg, #f0f3f6 0 5px, #f7f9fb 5px 10px);
  pointer-events: none;
  z-index: 1;
}

.reserve-block {
  position: absolute;
  left: 4px; right: 4px;
  border-radius: 8px;
  padding: 4px 8px;
  overflow: hidden;
  cursor: pointer;
  z-index: 2;
  transition: transform 0.15s;
}
.reserve-block:hover { transform: scale(1.02); }
.reserve-block.approved {
  background: linear-gradient(135deg, rgba(14,116,144,.92), rgba(34,160,184,.88));
  color: #fff;
  box-shadow: 0 3px 10px rgba(14,116,144,.35);
}
.reserve-block.pending {
  background: #fdf6e8;
  border: 1.5px dashed #f59e0b;
  color: #b45309;
}
.block-time { font-size: 11px; font-weight: 700; }
.block-name { font-size: 11.5px; margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
