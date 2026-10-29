<template>
  <div class="student-lab-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>实验室列表</h2>
    </div>

    <el-card class="box-card" shadow="never">
      <!-- 搜索栏 -->
      <el-form :inline="true" :model="queryParams" class="search-bar">
        <el-form-item>
          <el-input
            v-model="queryParams.keywords"
            placeholder="请输入名称查询"
            clearable
            style="width: 200px;"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button type="primary" @click="handleSearch" style="margin-left: 10px;">查询</el-button>
        </el-form-item>
      </el-form>

      <!-- 卡片式列表 -->
      <div v-loading="loading" class="lab-card-list">
        <el-row :gutter="20">
          <el-col :span="6" v-for="item in tableData" :key="item.id" style="margin-bottom: 20px;">
            <el-card class="lab-card" shadow="never" :body-style="{ padding: '0px' }">
              <!-- 封面图 -->
              <div class="lab-cover">
                <el-image
                  v-if="item.img"
                  :src="getImgUrl(item.img)"
                  fit="cover"
                  class="cover-img"
                >
                  <template #error>
                    <div class="image-placeholder"><el-icon><Picture /></el-icon></div>
                  </template>
                </el-image>
                <div v-else class="image-placeholder">
                  <el-icon><Picture /></el-icon>
                </div>
                <div class="cover-badge" :class="item.status === 1 ? 'open' : 'closed'">
                  <span class="badge-dot"></span>
                  {{ item.status === 1 ? '开放中' : '已关闭' }}
                </div>
                <div class="cover-gradient"></div>
              </div>

              <!-- 卡片内容 -->
              <div class="lab-info">
                <h3 class="lab-name">{{ item.name }}</h3>
                <div class="lab-meta-list">
                  <div class="meta-item">
                    <span class="meta-label">位置</span>
                    <span class="meta-value">{{ item.location || '-' }}</span>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">容量</span>
                    <span class="meta-value">{{ item.capacity }} 人</span>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">开放</span>
                    <span class="meta-value">{{ item.open_time || '--:--' }} - {{ item.close_time || '--:--' }}</span>
                  </div>
                </div>

                <!-- 操作按钮 -->
                <div class="lab-actions">
                  <el-button class="action-btn view-btn" @click="handleViewEquipments(item.id)">查看设备</el-button>
                  <el-button type="primary" class="action-btn book-btn" :disabled="item.status !== 1" @click="handleBook(item)">预约</el-button>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 空状态 -->
        <el-empty v-if="!loading && tableData.length === 0" description="暂无实验室数据" />
      </div>

      <!-- 分页组件 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :page-sizes="[8, 12, 16]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 预约弹窗组件 -->
    <ReserveDialog
      v-model="dialogVisible"
      :lab-id="selectedLab?.id"
      :lab-name="selectedLab?.name"
      @success="handleReservationSuccess"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Picture } from '@element-plus/icons-vue'
import { getlabList } from '@/api/lab'
// src/views/LabList.vue 和 src/views/LabEquipment.vue 都改成这样：
import ReserveDialog from '@/components/ReserveDialog.vue'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const router = useRouter()

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
// 后端 /lab/list 接收的关键字参数是 keywords
const queryParams = reactive({
  page: 1,
  page_size: 8,
  keywords: ''
})

// 预约相关状态
const dialogVisible = ref(false)
const selectedLab = ref(null)

const getImgUrl = (imgPath) => {
  if (!imgPath) return ''
  return imgPath.startsWith('http') ? imgPath : `${BASE_URL}${imgPath}`
}

const fetchList = async () => {
  loading.value = true
  try {
    const params = { ...queryParams }
    if (!params.keywords) delete params.keywords

    const res = await getlabList(params)
    if (res.code === 200) {
      tableData.value = res.data.list || []
      total.value = res.data.total || 0
    }
  } catch (error) {
    console.error('请求异常', error)
  } finally {
    loading.value = false
  }
}

const handleViewEquipments = (lab_id) => {
  router.push({ 
    path: '/manager/lab-equipment', 
    query: { lab_id } 
  })
}

// 点击预约按钮，打开弹窗
const handleBook = (lab) => {
  selectedLab.value = lab
  dialogVisible.value = true
}

// 预约成功回调
const handleReservationSuccess = () => {
  // 可以刷新列表等操作
}

const handleSearch = () => { queryParams.page = 1; fetchList() }
const handleSizeChange = (val) => { queryParams.page_size = val; queryParams.page = 1; fetchList() }
const handleCurrentChange = (val) => { queryParams.page = val; fetchList() }

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.student-lab-container { padding: 6px 2px 20px; }
.page-header { margin-bottom: 20px; }
.box-card { border-radius: 16px; }
.box-card :deep(.el-card__body) { padding: 20px; }
.search-bar { margin-bottom: 16px; padding: 14px 16px 0; background: #fafcfd; border-radius: 12px; border: 1px solid var(--lab-border); }

.lab-card-list { min-height: 200px; }

.lab-card {
  border-radius: 16px;
  overflow: hidden;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  border: 1px solid var(--lab-border);
}
.lab-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--lab-shadow-lg);
}

/* 封面 */
.lab-cover {
  position: relative;
  height: 150px;
  background-color: #e8eef2;
  overflow: hidden;
}
.cover-img { width: 100%; height: 100%; }
.lab-card:hover .cover-img :deep(img) {
  transform: scale(1.07);
}
.cover-img :deep(img) { transition: transform 0.4s ease; }

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #b8c6d1;
  font-size: 34px;
  background: linear-gradient(135deg, #edf2f5, #f7fafb);
}

/* 封面状态角标 */
.cover-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  backdrop-filter: blur(6px);
  z-index: 2;
}
.cover-badge.open {
  color: #0a9d5c;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 8px rgba(10, 157, 92, 0.25);
}
.cover-badge.closed {
  color: #8b98a8;
  background: rgba(255, 255, 255, 0.88);
}
.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.cover-badge.open .badge-dot { animation: dot-blink 1.8s infinite; }
@keyframes dot-blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

/* 底部渐变压暗，让角标更清晰 */
.cover-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(11, 26, 38, 0.12) 0%, transparent 40%);
  pointer-events: none;
}

/* 内容区 */
.lab-info { padding: 16px 16px 18px; }
.lab-name {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: var(--lab-text);
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.lab-meta-list {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.meta-item {
  display: flex;
  align-items: center;
  font-size: 13px;
  line-height: 1.5;
}
.meta-label {
  flex: 0 0 42px;
  color: var(--lab-text-3);
  font-size: 12px;
}
.meta-value {
  color: var(--lab-text-2);
  font-weight: 500;
}

.lab-actions { display: flex; justify-content: space-between; gap: 10px; }
.action-btn { flex: 1; border-radius: 9px; font-weight: 600; }
.view-btn { background: #f2f7f9; border-color: var(--lab-border); color: var(--lab-text-2); }
.view-btn:hover {
  background: #e8f1f4;
  border-color: rgba(14, 116, 144, 0.4);
  color: var(--lab-primary);
}
.book-btn { flex: 1; }

.pagination-container { display: flex; justify-content: flex-end; margin-top: 20px; }
</style>