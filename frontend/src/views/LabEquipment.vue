<template>
  <div class="lab-equipment-container">
    <!-- 顶部标题与操作 -->
    <div class="page-header">
      <div class="title-wrap">
        <h2>{{ labInfo?.name || '实验室' }}设备列表</h2>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="handleBookLab">预约实验室</el-button>
        <el-button @click="goBack">返回实验室列表</el-button>
      </div>
    </div>

    <!-- 实验室信息栏 -->
    <div class="lab-info-panel" v-if="labInfo">
      <div class="info-row">
        <span class="label">简介：</span>
        <span class="value">{{ labInfo.description || '暂无简介' }}</span>
      </div>
      <div class="info-row">
        <span class="label">位置：</span>
        <span class="value">{{ labInfo.location || '-' }}</span>
        <span class="divider">|</span>
        <span class="label">容纳：</span>
        <span class="value">{{ labInfo.capacity }} 人</span>
        <span class="divider">|</span>
        <span class="label">开放：</span>
        <span class="value">{{ labInfo.open_time || '--:--' }} - {{ labInfo.close_time || '--:--' }}</span>
      </div>
    </div>

    <el-card class="box-card" shadow="never">
      <!-- 表格区域 -->
      <el-table :data="tableData" v-loading="loading" style="width: 100%" :header-cell-style="{ background: '#f8f9fa', color: '#606266' }">
        <el-table-column label="图片" width="120" align="center">
          <template #default="scope">
            <el-image 
              v-if="scope.row.img" 
              :src="getImgUrl(scope.row.img)" 
              fit="cover"
              style="width: 60px; height: 60px; border-radius: 4px; border: 1px solid #ebeef5;"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="name" label="设备名称" min-width="150" />

        <el-table-column prop="spec" label="型号规格" min-width="180">
          <template #default="scope">{{ scope.row.spec || '-' }}</template>
        </el-table-column>

        <el-table-column prop="quantity" label="数量" width="100" align="center" />

        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag effect="light" :type="scope.row.status === 1 ? 'success' : 'info'">
              {{ scope.row.status === 1 ? '正常' : '维修中' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" align="center">
          <template #default="scope">
            <el-button type="primary" link @click="handleBookItem(scope.row)">预约</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页组件 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :page-sizes="[10, 20, 50]"
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
      :lab-id="labId"
      :equipment-id="selectedEquipment?.id"
      :lab-name="labInfo?.name"
      :equipment-name="selectedEquipment?.name"
      @success="handleReservationSuccess"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getequipmentList } from '@/api/equipment'
import { getLab } from '@/api/lab'
// src/views/LabList.vue 和 src/views/LabEquipment.vue 都改成这样：
import ReserveDialog from '@/components/ReserveDialog.vue'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const route = useRoute()
const router = useRouter()
const labId = route.query.lab_id

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const labInfo = ref(null)

// 预约相关状态
const dialogVisible = ref(false)
const selectedEquipment = ref(null)

const queryParams = reactive({
  page: 1,
  page_size: 10,
  keywords: '',
  lab_id: labId
})

const getImgUrl = (imgPath) => {
  if (!imgPath) return ''
  return imgPath.startsWith('http') ? imgPath : `${BASE_URL}${imgPath}`
}

// 获取实验室详情
const fetchLabInfo = async () => {
  if (!labId) return
  try {
    const res = await getLab(labId)
    if (res.code === 200) {
      labInfo.value = res.data
    }
  } catch (error) {
    console.error('获取实验室详情异常', error)
  }
}

// 获取设备列表
const fetchList = async () => {
  if (!labId) return
  loading.value = true
  try {
    const params = { ...queryParams }
    if (!params.keywords) delete params.keywords
    const res = await getequipmentList(params)
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

// 预约实验室
const handleBookLab = () => {
  selectedEquipment.value = null
  dialogVisible.value = true
}

// 预约设备
const handleBookItem = (row) => {
  selectedEquipment.value = row
  dialogVisible.value = true
}

// 预约成功回调
const handleReservationSuccess = () => {
  // 预约成功后可以刷新列表或做其他处理
  // fetchList() 
}

const goBack = () => {
  router.push('/manager/lablist')
}

const handleSizeChange = (val) => { queryParams.page_size = val; queryParams.page = 1; fetchList() }
const handleCurrentChange = (val) => { queryParams.page = val; fetchList() }

onMounted(() => {
  fetchLabInfo()
  fetchList()
})
</script>

<style scoped>
.lab-equipment-container { padding: 2px 2px 12px; }

/* 顶部区域 */
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.title-wrap h2 { margin: 0; font-size: 20px; color: #303133; font-weight: 600; }
.header-actions { display: flex; gap: 10px; }

/* 实验室信息面板（灰色背景条） */
.lab-info-panel {
  background-color: #f8f9fa;
  border-radius: 6px;
  padding: 15px 20px;
  margin-bottom: 20px;
  color: #606266;
  font-size: 14px;
}
.info-row { display: flex; align-items: center; line-height: 1.8; flex-wrap: wrap; }
.info-row .label { color: #909399; }
.info-row .value { color: #303133; margin-right: 5px; }
.info-row .divider { color: #dcdfe6; margin: 0 15px; }

/* 卡片和表格 */
.box-card { border-radius: 8px; }
.box-card :deep(.el-card__body) { padding: 20px; }

/* 分页 */
.pagination-container { display: flex; justify-content: flex-end; margin-top: 20px; }
</style>